# 📋 PRD: Smart Camera Vision Recognition Multi-Agent System

## 1.1 Product Vision
מערכת חכמה לזיהוי, ניתוח ותיעוד אובייקטים בזמן אמת מתוך מצלמת רשת, המבוססת על ארכיטקטורת **Multi-Agent** בפריימוורק **Agno**. המערכת מפעילה צוות סוכנים (Team of Agents) שמנתח פריימים מהמצלמה, מחלץ טקסט (OCR), מצליב את המידע מול היסטוריית זיהויים ב-**MongoDB Atlas**, מעשיר אותו בתובנות הקשריות וחושף את הנתונים דרך **Flask REST API**.

## 1.2 Core Objectives
- **פענוח ויזואלי מדויק:** זיהוי אובייקטים וקריאת טקסט (OCR) מתוך מצלמה חיה עם פלט מובנה (Structured Outputs).
- **אורקסטרציה של סוכנים (Orchestrator Pattern):** הפרדת אחריות בין סוכן ראייה (Vision Agent), סוכן זיכרון וידע (Knowledge Agent) וסוכן מתזמר (Orchestrator).
- **Context Engineering:** מניעת הצפת הקשר (Context Distraction) וחיסכון ב-Tokens על ידי שליחת פריימים מבוקרת ושליפת היסטוריה מתומצתת מ-MongoDB.
- **ארכיטקטורת Back End תעשייתית:** הפרדה מוחלטת לשכבות MVC, BLL ו-DAL.

## 1.3 Feature Proposals Matrix
| שם הפיצ'ר (Name) | פונקציונליות (Function) | אימפקט (Impact 1-5) |
| :--- | :--- | :---: |
| **Live Camera HUD & Capture** | תצוגת מצלמה חיה ב-OpenCV עם חיווי סטטוס על המסך וטריגר סריקה בלחיצת מקש `SPACE`. | 5 |
| **Vision Perception Agent** | סוכן המנתח את הפריים ומחלץ שם אובייקט, קטגוריה, טקסט (OCR), תיאור ויזואלי ורמת ודאות. | 5 |
| **Memory & Knowledge Agent** | סוכן המצויד בכלי (Tool) לתשאול MongoDB, בודק אם האובייקט נסרק בעבר ומייצר תובנה בעברית. | 5 |
| **MongoDB Atlas Persistence** | שמירה אוטומטית של כל רשומת זיהוי ב-Cluster בענן תחת סכמת Pydantic מאומתת. | 5 |
| **Flask REST API** | ממשק API לשליפת היסטוריית הזיהויים וחיפוש לפי שם אובייקט בפורמט JSON. | 4 |

## 1.4 User Workflow
1. המשתמש מפעיל את `main.py`; שרת ה-Flask עולה ברקע (פורט `5000`) וחלון המצלמה נפתח.
2. המשתמש מציג אובייקט מול המצלמה ולוחץ על `SPACE`.
3. ה-**Orchestrator** שולח את הפריים ל-**Vision Agent** שמחזיר אובייקט `VisionAnalysisResult`.
4. ה-**Orchestrator** מעביר את תוצאת הזיהוי ל-**Knowledge Agent**, שמתשאל את **MongoDB** באמצעות Function Calling ומייצר סיכום העשרה.
5. הרשומה המלאה (`DetectionRecord`) נשמרת ב-MongoDB דרך שכבת ה-DAL ומוצגת על המסך ובטרמינל.
