# views.py
import os
import json
import pandas as pd
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .forms import SalesCSVUploadForm, FilterForm
from .services.ingest import load_csv_to_mysql_and_clickhouse
from .services.kpi_queries import kpi
from .models import *
from .services.ch_client import get_client   # << ใช้ดึง channel จาก ClickHouse
from django.contrib.auth.forms import UserCreationForm

def register_view(request):
    # ถ้าล็อกอินอยู่แล้ว ไม่ต้องสมัครซ้ำ
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # สมัครสำเร็จแล้วล็อกอินให้ทันที
            messages.success(request, 'สมัครสมาชิกสำเร็จ ยินดีต้อนรับ 👋')
            return redirect('dashboard')
        else:
            messages.error(request, 'ไม่สามารถสมัครสมาชิกได้ โปรดตรวจสอบแบบฟอร์ม')
    else:
        form = UserCreationForm()

    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def upload_csv(request):
    if request.method == 'POST':
        form = SalesCSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                df = pd.read_csv(request.FILES['file'], encoding='utf-8-sig')
                load_csv_to_mysql_and_clickhouse(df)
                messages.success(request, 'อัปโหลดและบันทึกข้อมูลสำเร็จ')
                return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'เกิดข้อผิดพลาด: {e}')
    else:
        form = SalesCSVUploadForm()
    return render(request, 'upload.html', {'form': form})


def _channel_choices_from_clickhouse():
    """
    โหลดรายการ channel จาก ClickHouse ถ้ามีคอลัมน์ channel
    """
    ch = get_client()
    try:
        # เช็คว่ามีคอลัมน์ channel ไหม
        cols = [r[0] for r in ch.query("DESCRIBE TABLE analytics.fact_sales").result_rows]
        if 'channel' not in cols:
            return [('', 'ทุกช่องทาง')]

        rows = ch.query("SELECT DISTINCT channel FROM analytics.fact_sales WHERE channel != '' ORDER BY channel").result_rows
        opts = [('', 'ทุกช่องทาง')] + [(r[0], r[0]) for r in rows if r and r[0]]
        return opts or [('', 'ทุกช่องทาง')]
    except Exception:
        return [('', 'ทุกช่องทาง')]



# views.py (เฉพาะส่วน dashboard)
@login_required
def dashboard(request):
    f = FilterForm(request.GET or None)
    # เติมตัวเลือก channel จากฐานจริง (ต้องทำก่อนอ่านค่า value)
    f.fields['channel'].choices = _channel_choices_from_clickhouse()

    start   = f['start_date'].value()
    end     = f['end_date'].value()
    channel = f['channel'].value() or None

    # >>> รับค่ากลับ 5 ชุดจาก kpi()
    top_df, hour_df, day_df, channel_df, day_cum_df = kpi(start=start, end=end, channel=channel)

    # ---------- ติดชื่อเมนูให้ Top ----------
    top_rows = top_df.to_dict(orient='records')
    sku_list = [r['sku'] for r in top_rows] if top_rows else []
    name_map = {m.sku: m.name for m in MenuItem.objects.filter(sku__in=sku_list)}
    top_with_names = []
    for r in top_rows:
        sku = r['sku']
        name = (name_map.get(sku) or '').strip()
        r['menu_label'] = f"{name}" if name else sku
        top_with_names.append(r)
    # ---------------------------------------

    ctx = {
        'filter': f,
        'top': top_with_names,
        'hour': hour_df.to_dict(orient='records'),           # มี rev, orders, aov
        'day': day_df.to_dict(orient='records'),
        'channel': channel_df.to_dict(orient='records'),     # อาจว่างถ้าไม่มีคอลัมน์
        'day_cum': day_cum_df.to_dict(orient='records'),     # d, rev, cum_rev
    }
    return render(request, 'dashboard.html', ctx)


def _call_openrouter(prompt_text: str) -> str:
    from openai import OpenAI
    base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
    api_key  = os.getenv('OPENROUTER_API_KEY')
    model    = os.getenv('OPENROUTER_MODEL', 'meta-llama/llama-3.3-70b-instruct')
    if not api_key:
        raise RuntimeError('OPENROUTER_API_KEY is not set')

    # header แนะนำโดย OpenRouter (ไม่บังคับ)
    default_headers = {}
    if os.getenv('OPENROUTER_SITE_URL'):
        default_headers['HTTP-Referer'] = os.getenv('OPENROUTER_SITE_URL')
    if os.getenv('OPENROUTER_APP_NAME'):
        default_headers['X-Title'] = os.getenv('OPENROUTER_APP_NAME')

    client = OpenAI(base_url=base_url, api_key=api_key, default_headers=default_headers or None)

    resp = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt_text}],
    )
    return resp.choices[0].message.content.strip()

# ---------- HELPER: เรียก Gemini ----------
def _call_gemini(prompt_text: str) -> str:
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(
        model=os.getenv('GEMINI_MODEL', 'gemini-1.5-flash'),
        google_api_key=os.getenv('GOOGLE_API_KEY'),
        temperature=0.2,
    )
    res = llm.invoke(prompt_text)
    return getattr(res, 'content', str(res)).strip()

# ---------- API SUMMARY (ใช้ OpenRouter เป็นหลัก, Gemini สำรอง) ----------
@login_required
def api_summary(request):
    try:
        # 1) อ่านตัวกรอง
        f = FilterForm(request.GET or None)
        start   = f['start_date'].value()
        end     = f['end_date'].value()
        channel = f['channel'].value() or None

        # 2) ดึง KPI  <<< สำคัญ: รับ 5 ค่า
        top_df, hour_df, day_df, _, _ = kpi(start=start, end=end, channel=channel)

        # 3) เตรียม Top เป็นชื่อเมนูอ่านง่าย
        top_rows = top_df.to_dict(orient='records')
        sku_list = [r['sku'] for r in top_rows] if top_rows else []
        name_map = {m.sku: m.name for m in MenuItem.objects.filter(sku__in=sku_list)}
        top_for_ai = []
        for r in top_rows:
            sku  = r['sku']
            name = (name_map.get(sku) or '').strip()
            top_for_ai.append({
                "menu": name if name else sku,
                "sku": sku,
                "qty": int(r.get("total_qty", 0)),
                "revenue": float(r.get("revenue", 0)),
            })

        # 4) ประกอบ prompt เป็นสตริงล้วน + ฝัง JSON (ปลอดภัยต่อ parsing)
        import json as _json
        parts = []
        parts.append("คุณเป็นผู้ช่วยวิเคราะห์ข้อมูลร้านอาหาร ตอบภาษาไทย กระชับ และมีหัวข้อย่อยชัดเจน")
        if start or end or channel:
            parts.append(f"ช่วงเวลา: {start or '-'} ถึง {end or '-'} | ช่องทาง: {channel or 'ทุกช่องทาง'}")
        parts.append("ให้สรุปว่า: 1) เมนูขายดี 3 อันดับ(เอาจำนวนที่เยอะที่สุด และบอกรายได้รวม) 2) ชั่วโมงรายได้สูงสุด 3) แนวโน้มรายวัน (อธิบายและเปรียบเทียบยอดขายรวมของวันนี้กับวันก่อนหน้า (เพิ่มขึ้น/ลดลงกี่เปอร์เซ็นต์)) 4) ไอเดียโปรโมชัน 2-3 ข้อ(แนะนำไอเดียโปรโมชันที่น่าสนใจ 2-3 ข้อ โดยอิงจากข้อมูลเมนูขายดีและช่วงเวลาที่มีลูกค้ามากที่สุด) 5)ภาพรวมทั้งหมด")
        parts.append(f"[Top Menus] {_json.dumps(top_for_ai, ensure_ascii=False)}")
        parts.append(f"[Revenue by Hour] {hour_df.to_json(orient='records', force_ascii=False)}")
        parts.append(f"[Revenue by Day]  {day_df.to_json(orient='records',  force_ascii=False)}")
        prompt_text = "\n".join(parts)

        # 5) เรียก LLM (OpenRouter -> fallback Gemini)
        provider = (os.getenv('LLM_PROVIDER') or 'openrouter').lower()

        summary = ""
        errors = []

        if provider in ('openrouter', 'auto'):
            try:
                summary = _call_openrouter(prompt_text)
            except Exception as e:
                errors.append(f"openrouter: {e}")

        if not summary:
            try:
                summary = _call_gemini(prompt_text)
            except Exception as e:
                errors.append(f"gemini: {e}")

        if not summary:
            return JsonResponse({"summary": "", "error": " | ".join(errors) or "LLM error"}, status=200)

        return JsonResponse({"summary": summary})

    except Exception as e:
        return JsonResponse({"summary": "", "error": f"{type(e).__name__}: {e}"}, status=200)

