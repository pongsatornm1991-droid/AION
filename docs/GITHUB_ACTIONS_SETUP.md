# ตั้งค่า AION ให้ทำงานอัตโนมัติ 24 ชม. (GitHub Actions)

คู่มือนี้เป็นขั้นตอน **ทำครั้งเดียว** ให้ AION ตอบคอมเมนต์ + โพสต์เองได้
ตลอดเวลา โดยไม่ต้องเปิดเครื่องคอมพิวเตอร์ทิ้งไว้ และไม่ต้องกดรันเองอีกเลย
รันอยู่บนเซิร์ฟเวอร์ของ GitHub เอง (ฟรี เพราะ repo นี้เป็น public)

มี 5 ขั้นตอน ทำครั้งเดียวจบ ข้อ 1 ทำในเครื่องคุณ ข้อ 2-5 ทำบนเว็บ github.com

---

## ขั้นตอนที่ 1: push โค้ดขึ้น GitHub (ทำในเครื่องคุณ)

เปิด terminal/PowerShell ที่ `C:\Projects\AION` แล้วรัน:

```powershell
git push origin main
```

(ขั้นตอนนี้ Claude ทำแทนไม่ได้ เพราะต้องใช้ GitHub credential ที่ผูกกับ
เครื่องคุณเองเท่านั้น)

---

## ขั้นตอนที่ 2: สร้าง repo ส่วนตัวสำหรับเก็บความจำของ AION

ความจำ (memory) ของ AION ไม่ได้เก็บใน repo หลัก (ตั้งใจไว้แต่แรก เพราะ repo
หลักเป็น public) เลยต้องมี repo แยกต่างหาก แบบ **private** ไว้เก็บโดยเฉพาะ

1. ไปที่ https://github.com/new
2. ตั้งชื่อ repo ว่า **`aion-memory-data`** (ต้องตรงตัวนี้เป๊ะ เพราะ workflow
   อ้างชื่อนี้ไว้แล้ว)
3. เลือก **Private**
4. ติ๊ก "Add a README file" (สำคัญ — ต้องมีไฟล์เริ่มต้นอย่างน้อย 1 ไฟล์)
5. กด Create repository

---

## ขั้นตอนที่ 3: สร้าง Personal Access Token (PAT)

Token นี้ให้สิทธิ์ workflow เขียนเข้า repo `aion-memory-data` ได้

1. ไปที่ https://github.com/settings/tokens?type=beta (Fine-grained tokens)
2. กด "Generate new token"
3. Repository access: เลือก "Only select repositories" → เลือก
   `aion-memory-data`
4. Permissions → Repository permissions → **Contents: Read and write**
5. กด Generate token แล้ว **copy ค่า token ไว้** (จะเห็นครั้งเดียว)

---

## ขั้นตอนที่ 4: เพิ่ม Secrets ใน repo หลัก (AION)

ไปที่ https://github.com/pongsatornm1991-droid/AION/settings/secrets/actions
แล้วกด "New repository secret" ทีละอัน ตามรายการนี้:

| ชื่อ Secret | ค่าที่ใส่ |
|---|---|
| `MEMORY_REPO_PAT` | Token จากขั้นตอนที่ 3 |
| `GEMINI_API_KEY` | ค่าเดียวกับที่อยู่ใน `.env` ในเครื่องตอนนี้ |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | ค่าเดียวกับที่อยู่ใน `.env` |
| `FACEBOOK_PAGE_ID` | ค่าเดียวกับที่อยู่ใน `.env` |
| `TELEGRAM_BOT_TOKEN` | ค่าเดียวกับที่อยู่ใน `.env` (ถ้าอยากได้แจ้งเตือน) |
| `TELEGRAM_CHAT_ID` | ค่าเดียวกับที่อยู่ใน `.env` (ถ้าอยากได้แจ้งเตือน) |

ค่าจริงพวกนี้ Claude ไม่เห็นและไม่แตะเลย — คุณต้อง copy จากไฟล์ `.env` ใน
เครื่องมาใส่เอง (เปิดไฟล์ `.env` ด้วย Notepad ดูค่าได้)

---

## ขั้นตอนที่ 5: ตรวจสอบว่ารันจริง

1. ไปที่ https://github.com/pongsatornm1991-droid/AION/actions
2. ควรเห็น workflow ชื่อ "AION - check comments" และ "AION - social post
   cycle" อยู่ในรายการ
3. กดเข้า workflow แต่ละอัน แล้วกด "Run workflow" เพื่อทดสอบรันทันทีครั้งแรก
   (ไม่ต้องรอตามตาราง)
4. ดูผลลัพธ์ในหน้า log — ถ้า error เรื่อง credential ให้กลับไปเช็คขั้นตอนที่ 4

---

## หลังจากนี้

- **ตอบคอมเมนต์**: รันเองทุก 5 นาที ตลอด 24 ชม. ไม่ต้องทำอะไรอีก
- **โพสต์ใหม่**: รันเองทุก 6 ชม. (วันละ 4 ครั้ง) — ปรับความถี่ได้ที่ไฟล์
  `.github/workflows/social-cycle.yml` บรรทัด `cron:`
- Task Scheduler ที่ตั้งไว้ในเครื่องเดิม (ถ้าตั้งไว้แล้ว) **ปิดได้เลย** ไม่
  จำเป็นอีกต่อไป เพราะ GitHub รันแทนให้ตลอด ไม่ต้องเปิดเครื่อง

## ข้อควรรู้

- GitHub จะ**ปิด schedule อัตโนมัติถ้า repo ไม่มี commit ใหม่เกิน 60 วัน** —
  ถ้าไม่ได้แก้โค้ดนานๆ ให้เข้าไป push อะไรเล็กๆ น้อยๆ บ้าง (หรือกด "Run
  workflow" มือเองครั้งหนึ่งก็พอ จะรีเซ็ตนับใหม่)
- เวลาที่รันจริงอาจคลาดเคลื่อนจากตารางเล็กน้อยได้ (ไม่ใช่ real-time แม่นยำ
  วินาทีต่อวินาที) เป็นเรื่องปกติของ GitHub Actions scheduler
