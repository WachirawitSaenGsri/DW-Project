
 # ระบบวิเคราะห์ยอดขายร้านอาหารพร้อมแนะนำเมนูยอดนิยม
 
  # สมาชิก
  
  - 1.นายวชิรวิทย์ แสงศรี 65114540534
    
  - 2.นายฐิติวัฒน์ แจ่มศรี 65114540156
    
  - 3.นายอิทธิพัทธ์ ประชุมรักษ์ 65114540745
    
  - 4.นายวรรธิษณุ์ จุรัยจิราสพล 6511454054
    
  # วัตถุประสงค์
  
  - เพื่อวิเคราะห์ข้อมูลยอดขายและพฤติกรรมการสั่งซื้อของลูกค้าโดยแสดงผลในรูปแบบรายงาน สถิติกราฟและสรุปผลที่เข้าใจง่ายช่วยให้ผู้ประกอบการสามารถติดตามยอดขายและแนวโน้มความต้องการ
    ได้อย่างมีประสิทธิภาพ

    
  - เพื่อประยุกต์ใช้เทคโนโลยี Generative AI ในการสร้างข้อความสรุป วิเคราะห์ และแนะนำข้อมูล เช่น เมนูยอดนิยม ช่วงเวลายอดขายสูง หรือข้อเสนอแนะแนวทางการจัดโปรโมชั่น
  - เพื่อยกระดับคุณภาพการให้บริการและความพึงพอใจของลูกค้า ด้วยข้อมูลเชิงลึก ที่สามารถนำไปปรับปรุงประสบการณ์ลูกค้าได้ตรงจุด

   # เครื่องมือ
   
  - ClickHouse และฐานข้อมูล MySQL
    
  - Generative AI ที่ใช้ Llama
    
  - Application Framework ที่จะนำมาพัฒนาแอปพลิเคชัน Django

   # ลิงก์วีดีโอ นำเสนอโครงการ  (อยู่ใน Google drive / เข้าถึงได้โดยอีเมล์ wichit.s@ubu.ac.th)

      



	  
# คำสั่งสำหรับรัน

docker compose build

docker compose up -d

docker compose exec clickhouse clickhouse-client -q "CREATE USER app_user IDENTIFIED WITH plaintext_password BY 'StrongP@ss!' HOST ANY;"

docker compose exec clickhouse clickhouse-client -q "GRANT SELECT, INSERT, CREATE, ALTER ON analytics.* TO app_user;"

docker compose exec clickhouse clickhouse-client -q "ALTER USER app_user IDENTIFIED WITH plaintext_password BY 'StrongP@ss!' HOST ANY;"

docker compose exec clickhouse clickhouse-client -q "GRANT SELECT, INSERT, CREATE, ALTER ON analytics.* TO app_user;"

docker compose exec clickhouse clickhouse-client -q "GRANT SELECT, INSERT ON analytics.* TO app_user"

docker compose exec clickhouse clickhouse-client -q "GRANT TRUNCATE ON analytics.* TO app_user"

docker compose exec clickhouse clickhouse-client -q "GRANT ALTER ON analytics.* TO app_user"

docker compose exec web bash -lc "python manage.py makemigrations"

docker compose exec web bash -lc "python manage.py migrate"

docker compose exec web bash -lc "python manage.py createsuperuser" 

docker compose exec clickhouse clickhouse-client -q "
CREATE TABLE IF NOT EXISTS analytics.fact_sales
(
  order_id String,
  order_ts DateTime,
  sku String,
  qty Int32,
  gross_amount Decimal(12,2),
  discount Decimal(12,2),
  net_amount Decimal(12,2)
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(order_ts)
ORDER BY (order_ts, sku)
SETTINGS index_granularity = 8192;
"

docker compose exec clickhouse clickhouse-client -q "
ALTER TABLE analytics.fact_sales
ADD COLUMN IF NOT EXISTS channel LowCardinality(String) DEFAULT '';
"

ไฟล์ข้อมูลทดลองอยู่ในไฟล์ scripts 
