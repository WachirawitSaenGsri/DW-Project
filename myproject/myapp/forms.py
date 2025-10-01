from django import forms

class SalesCSVUploadForm(forms.Form):
    file = forms.FileField(widget=forms.FileInput(attrs={
        "id": "csvFile",
        "class": "hidden",
        "accept": ".csv",
    }))

class FilterForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end_date   = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    channel    = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ตั้งค่าเริ่มต้นไว้ก่อน แล้ว view จะมาอัปเดตเป็นรายการจริง
        self.fields['channel'].choices = [('', 'ทุกช่องทาง')]
