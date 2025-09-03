# CRM Celery Setup

## Requirements
- Redis
- Celery
- django-celery-beat

## Setup Steps

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
# CRM Celery Setup

This project uses **Celery** with **Celery Beat** to schedule tasks.  
A weekly report is generated every Monday at 6 AM, summarizing total customers, orders, and revenue.  
The report is logged to `/tmp/crm_report_log.txt`.

---

## Setup Steps

### 1. Install Dependencies
Make sure you have Python and pip installed.

```bash
pip install -r requirements.txt
