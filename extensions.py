#!/usr/bin/env python3
"""
Mail AI Sorter - Erweiterungen mit Open Source Tools
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
import sqlite3
import re

class PaperlessNGXIntegration:
    """Integration mit Paperless-ngx"""

    def __init__(self, paperless_url="http://localhost:8000", api_token=None):
        self.paperless_url = paperless_url
        self.api_token = api_token or self.get_token_from_env()

    def get_token_from_env(self):
        """Token aus Umgebungsvariable lesen"""
        import os
        return os.getenv("PAPERLESS_API_TOKEN")

    def create_document_from_email(self, email_data):
        """Erstellt ein Dokument in Paperless-ngx aus einer Email"""
        import requests

        # PDF aus Email extrahieren
        pdf_data = self.extract_pdf_from_email(email_data)

        # Metadaten vorbereiten
        metadata = {
            "title": email_data.get("subject", "Unbekannt"),
            "created": email_data.get("date_iso", ""),
            "document_type": self.guess_document_type(email_data),
            "tags": self.extract_tags(email_data)
        }

        # An Paperless-ngx senden
        files = {"document": pdf_data}
        response = requests.post(
            f"{self.paperless_url}/api/documents/post_document/",
            files=files,
            data=metadata,
            headers={"Authorization": f"Token {self.api_token}"}
        )

        return response.json()

    def guess_document_type(self, email_data):
        """Errät Dokumenten-Typ basierend auf Email-Kategorie"""
        category = email_data.get("category", "")

        type_mapping = {
            "paperless": "Rechnung",
            "finanzen": "Kontoauszug",
            "einkauf": "Bestellung",
            "vertraege": "Vertrag",
            "arbehoerden": "Bescheid",
            "versicherung": "Versicherung",
            "recht": "Klage"
        }

        return type_mapping.get(category, "Allgemein")

    def extract_pdf_from_email(self, email_data):
        """Extrahiert PDF-Anhänge aus Email"""
        # Implementierung mit email图书馆
        pass

    def extract_tags(self, email_data):
        """Extrahiert Tags aus Email-Daten"""
        tags = [email_data.get("category", "unbekannt")]

        # Absender-Domain als Tag
        from_addr = email_data.get("from_addr", "")
        if "@" in from_addr:
            domain = from_addr.split("@")[1]
            tags.append(domain)

        return tags


class CalendarIntegration:
    """Integration mit Kalender-Tools"""

    def __init__(self):
        self.events = []

    def extract_appointments(self, email_data):
        """Extrahiert Termine aus Emails"""
        text = f"{email_data.get('subject', '')} {email_data.get('body', '')}"

        # Datums-Muster
        date_patterns = [
            r'\d{1,2}\.\s*\d{1,2}\.\s*\d{4}',  # 15. 04. 2026
            r'\d{4}-\d{2}-\d{2}',              # 2026-04-15
            r'\d{1,2}/\d{1,2}/\d{4}',          # 15/04/2026
        ]

        # Zeit-Muster
        time_patterns = [
            r'\d{1,2}:\d{2}',                 # 14:30
            r'\d{1,2}\.\d{2} Uhr',             # 14.30 Uhr
        ]

        appointments = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            appointments.extend(matches)

        return appointments

    def create_calendar_event(self, appointment, email_data):
        """Erstellt einen Kalender-Eintrag"""
        import subprocess

        # gcalcli (Google Calendar CLI)
        cmd = [
            "gcalcli",
            "--calendar", "Hauptkalender",
            "add",
            "--title", email_data.get("subject", "Termin"),
            "--when", appointment,
            "--description", email_data.get("from_addr", ""),
            "--duration", "60"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            print("gcalcli nicht installiert. Installiere mit: brew install gcalcli")
            return False


class TaskIntegration:
    """Integration mit Task-Management-Tools"""

    def __init__(self, task_system="taskwarrior"):
        self.task_system = task_system

    def create_task_from_email(self, email_data):
        """Erstellt eine Aufgabe aus einer Email"""
        subject = email_data.get("subject", "")
        from_addr = email_data.get("from_addr", "")
        category = email_data.get("category", "")

        # Task-Beschreibung
        task_description = f"{subject} (Von: {from_addr}, Kategorie: {category})"

        if self.task_system == "taskwarrior":
            return self.create_taskwarrior_task(task_description)
        elif self.task_system == "todo.txt":
            return self.create_todo_txt_task(task_description)

    def create_taskwarrior_task(self, description):
        """Erstellt Taskwarrior-Aufgabe"""
        import subprocess

        cmd = ["task", "add", description]
        result = subprocess.run(cmd, capture_output=True, text=True)

        return result.returncode == 0

    def create_todo_txt_task(self, description):
        """Erstellt todo.txt Aufgabe"""
        todo_file = Path.home() / "todo.txt"

        with open(todo_file, "a") as f:
            f.write(f"{description}\n")

        return True


class NotificationIntegration:
    """Integration mit Benachrichtigungs-Tools"""

    def send_notification(self, title, message, urgency="normal"):
        """Sendet Desktop-Benachrichtigung"""
        import subprocess

        # macOS notify-send
        cmd = [
            "osascript",
            "-e", f'display notification "{message}" with title "{title}"'
        ]

        try:
            subprocess.run(cmd, capture_output=True)
            return True
        except Exception as e:
            print(f"Benachrichtigung fehlgeschlagen: {e}")
            return False

    def notify_important_email(self, email_data):
        """Benachrichtigt bei wichtiger Email"""
        category = email_data.get("category", "")
        important_categories = ["arbeit", "finanzen", "behoerden", "vertraege"]

        if category in important_categories:
            subject = email_data.get("subject", "")
            from_addr = email_data.get("from_addr", "")

            self.send_notification(
                f"📧 {category.upper()} Email",
                f"Von: {from_addr}\nBetreff: {subject}",
                urgency="critical"
            )


class AnalyticsIntegration:
    """Integration mit Analytics-Tools"""

    def __init__(self, db_path="mail_index.db"):
        self.db_path = db_path

    def generate_statistics(self):
        """Generiert detaillierte Statistiken"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Emails pro Stunde
        hourly_distribution = cursor.execute("""
            SELECT
                CAST(strftime('%H', date_iso) AS INTEGER) as hour,
                COUNT(*) as count
            FROM emails
            GROUP BY hour
            ORDER BY hour
        """).fetchall()

        # Emails pro Wochentag
        weekday_distribution = cursor.execute("""
            SELECT
                CAST(strftime('%w', date_iso) AS INTEGER) as weekday,
                COUNT(*) as count
            FROM emails
            GROUP BY weekday
            ORDER BY weekday
        """).fetchall()

        # Top Absender
        top_senders = cursor.execute("""
            SELECT
                from_addr,
                COUNT(*) as count
            FROM emails
            GROUP BY from_addr
            ORDER BY count DESC
            LIMIT 20
        """).fetchall()

        conn.close()

        return {
            "hourly": dict(hourly_distribution),
            "weekday": dict(weekday_distribution),
            "top_senders": dict(top_senders)
        }

    def export_to_csv(self, output_file="email_statistics.csv"):
        """Exportiert Statistiken als CSV"""
        import csv

        stats = self.generate_statistics()

        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)

            writer.writerow(["Kategorie", "Wert"])
            for key, value in stats["top_senders"].items():
                writer.writerow(["Absender", key, value])


class AIAutomationExtensions:
    """KI-Automatisierungs-Erweiterungen"""

    def __init__(self, ollama_url="http://127.0.0.1:11434"):
        self.ollama_url = ollama_url

    def summarize_email(self, email_data):
        """Zusammenfasst eine Email mit KI"""
        import requests

        subject = email_data.get("subject", "")
        body = email_data.get("body", "")

        prompt = f"""Zusammenfasse diese Email kurz:

Betreff: {subject}
Inhalt: {body}

Erstelle eine Zusammenfassung in max. 3 Sätzen."""

        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False
            }
        )

        if response.ok:
            return response.json().get("response", "")
        return None

    def extract_entities(self, email_data):
        """Extrahiert Entitäten (Termine, Beträge, etc.)"""
        import requests

        text = f"{email_data.get('subject', '')}\n{email_data.get('body', '')}"

        prompt = f"""Extrahiere wichtige Informationen aus dieser Email:

Email:
{text)}

Erkenne und extrahiere:
- Datum/Uhrzeit (falls vorhanden)
- Geldbeträge (falls vorhanden)
- Telefonnummern (falls vorhanden)
- Namen (falls vorhanden)

Formatiere als JSON:
{{
    "dates": ["YYYY-MM-DD HH:MM"],
    "amounts": ["EUR 123.45"],
    "phone_numbers": ["+49 123 456789"],
    "names": ["Max Mustermann"]
}}
"""

        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False
            }
        )

        if response.ok:
            return response.json().get("response", "")
        return None


class BackupIntegration:
    """Backup-Integration"""

    def backup_emails_to_markdown(self, output_dir="email_backups"):
        """Backup Emails als Markdown"""
        import os

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        conn = sqlite3.connect("mail_index.db")
        cursor = conn.cursor()

        emails = cursor.execute("""
            SELECT id, subject, from_addr, date_iso, category, body
            FROM emails
            ORDER BY date_iso DESC
        """).fetchall()

        for email in emails:
            email_id, subject, from_addr, date_iso, category, body = email

            filename = f"{date_iso[:10]}_{category}_{email_id}.md"
            filepath = output_path / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# {subject}\n\n")
                f.write(f"**Von:** {from_addr}\n")
                f.write(f"**Datum:** {date_iso}\n")
                f.write(f"**Kategorie:** {category}\n\n")
                f.write(f"**Inhalt:**\n\n{body}\n")

        conn.close()
        return len(emails)


if __name__ == "__main__":
    # Beispiel für alle Integrationen
    print("🔧 Mail AI Sorter - Erweiterungen")
    print("=" * 50)

    # Paperless-ngx
    print("1. Paperless-ngx Integration")
    paperless = PaperlessNGXIntegration()
    print("   - Automatische Dokumenten-Erkennung")
    print("   - Tag-Generierung aus Kategorien")
    print("   - API-Schnittstelle")

    # Kalender
    print("2. Kalender-Integration")
    calendar = CalendarIntegration()
    print("   - Termin-Extrahierung aus Emails")
    print("   - gcalcli Support")
    print("   - Automatische Eintrag-Erstellung")

    # Tasks
    print("3. Task-Management")
    tasks = TaskIntegration()
    print("   - taskwarrior Support")
    print("   - todo.txt Support")
    print("   - Automatische Aufgaben-Generierung")

    # Benachrichtigungen
    print("4. Benachrichtigungen")
    notifications = NotificationIntegration()
    print("   - macOS Notifications")
    print("   - Wichtige Emails sofort anzeigen")

    # Analytics
    print("5. Analytics")
    analytics = AnalyticsIntegration()
    print("   - Email-Statistiken")
    print("   - CSV-Export")
    print("   - Visualisierung möglich")

    # KI-Erweiterungen
    print("6. KI-Automatisierung")
    ai = AIAutomationExtensions()
    print("   - Email-Zusammenfassungen")
    print("   - Entitäten-Extraktion")
    print("   - Intelligente Priorisierung")

    # Backup
    print("7. Backup")
    backup = BackupIntegration()
    print("   - Markdown-Export")
    print("   - Volltext-Backup")

    print("\n📦 Alle Erweiterungen sind Open Source!")
    print("=" * 50)
