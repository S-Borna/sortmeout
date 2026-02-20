"""Generate SORTMEOUT_OVERVIEW.pdf matching the CodeTrust overview design."""

from weasyprint import HTML

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@400;600;700&display=swap');

  @page {
    size: A4;
    margin: 32mm 30mm 22mm 30mm;
  }

  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    color: #1a1a2e;
    line-height: 1.5;
    font-size: 9pt;
  }

  h1.title {
    font-family: 'Playfair Display', Georgia, 'Times New Roman', serif;
    font-weight: 900;
    font-size: 28pt;
    letter-spacing: -0.5px;
    margin-bottom: 2px;
    color: #111;
  }

  .subtitle {
    font-size: 9.5pt;
    margin-bottom: 1px;
    color: #333;
  }

  .subtitle strong {
    font-weight: 700;
  }

  .version {
    font-size: 8.5pt;
    color: #555;
    margin-bottom: 12px;
  }

  hr {
    border: none;
    border-top: 1px solid #e0e0e0;
    margin: 10px 0;
  }

  .section-header {
    font-size: 7.5pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    color: #6C5CE7;
    margin-bottom: 6px;
    margin-top: 12px;
  }

  .section-body {
    font-size: 8.8pt;
    color: #2d2d44;
    line-height: 1.55;
    margin-bottom: 2px;
    text-align: justify;
    hyphens: auto;
  }

  .footer {
    text-align: center;
    margin-top: 16px;
    padding-top: 8px;
    border-top: 1px solid #e0e0e0;
  }

  .footer strong {
    font-size: 8.5pt;
    color: #333;
  }

  .footer .sub {
    font-size: 7.5pt;
    color: #777;
    margin-top: 1px;
  }
</style>
</head>
<body>

<h1 class="title">SortMeOut</h1>
<div class="subtitle"><strong>AI-Powered Desktop Automation for macOS</strong></div>
<div class="version">v1.0.1 — Created by Said Borna</div>

<hr>

<div class="section-header">What it does</div>
<div class="section-body">
SortMeOut is a native macOS desktop application that combines intelligent file automation with a full-spectrum AI assistant. It watches folders in real-time and organizes files the moment they appear — matching against user-defined rules with 17 condition types and 22 action types. Beyond file management, the built-in AI assistant powered by Claude acts as a complete desktop companion: it executes 31 system commands spanning file operations, Spotlight search, Finder tags, email, calendar, contacts, presentations, system control, and more — all from natural language. An integrated Image Studio powered by DALL·E 3 adds on-device image generation, editing, and conversion. The entire experience lives in the macOS menu bar as a single, always-available app.
</div>

<div class="section-header">The vision</div>
<div class="section-body">
The Mac ecosystem lacks a unified automation layer that thinks for you. Existing tools handle one thing — file sorting, or scripting, or AI chat — but none combine them into a single intelligent surface that understands your desktop, your schedule, your files, and your intent. SortMeOut is being built to become that surface: a personal operations layer for macOS that replaces five separate utilities with one AI-native application. The ambition is a product that competes directly with established players like Hazel, Raycast, and Alfred — but goes further by integrating deep Apple ecosystem access with conversational AI that can actually execute.
</div>

<div class="section-header">Why it exists</div>
<div class="section-body">
Power users and professionals on macOS still manage their digital workspace manually. Files pile up, workflows stay fragmented, and system-level tasks require jumping between apps, terminals, and settings panels. AI assistants exist, but they answer questions — they don't act. SortMeOut was built for the gap between knowing what needs to happen and having it happen automatically: real automation, real execution, real integration with the operating system.
</div>

<div class="section-header">Current state</div>
<div class="section-body">
SortMeOut is in active development with a functional product already built and running. The rule engine, AI assistant, Image Studio, and all macOS integrations are operational and validated by 301 automated tests. The application ships as a standalone .app bundle. Development is ongoing with a clear roadmap toward a polished, market-ready release — focused on first-run experience, persistent AI conversations, and expanded Apple ecosystem depth. This is not a prototype; it is an early-stage product being built to enterprise-grade quality with the ambition to compete at scale.
</div>

<div class="footer">
  <strong>sortmeout.saidborna.com</strong>
  <div class="sub">saidborna.com</div>
</div>

</body>
</html>"""

OUTPUT_PATH = "/Users/REDACTED/Desktop/DevOps/Sortmeout/sortmeout/docs/SORTMEOUT_OVERVIEW.pdf"

HTML(string=HTML_CONTENT).write_pdf(OUTPUT_PATH)
print(f"PDF generated: {OUTPUT_PATH}")
