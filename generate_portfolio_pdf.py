from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import os

pdf_path = r'C:\Users\saini\Desktop\Sai_Nihal_AI_Portfolio.pdf'
doc = SimpleDocTemplate(pdf_path, pagesize=letter)
styles = getSampleStyleSheet()

title_style = styles['Heading1']
sub_style = styles['Heading2']
title_style.textColor = '#2c3e50'
sub_style.textColor = '#34495e'

p_style = styles['Normal']
p_style.fontSize = 11
p_style.leading = 16

elements = []
elements.append(Paragraph('<b>Sai Nihal</b>', title_style))
elements.append(Paragraph('<b>AI Pilot & Data Extraction Specialist</b>', p_style))
elements.append(Spacer(1, 25))

elements.append(Paragraph('AI DATA PIPELINE PROJECTS', sub_style))
elements.append(Spacer(1, 15))

elements.append(Paragraph('<b>1. Mindrift — AI Data Production & Validation Platform</b>', styles['Heading3']))
elements.append(Paragraph('<a href="https://stunning-friendship-production-94b6.up.railway.app" color="blue">Live Demo</a> | <a href="https://github.com/SaiNihal2622/ai-data-extraction-platform" color="blue">GitHub</a>', p_style))
elements.append(Spacer(1, 15))

elements.append(Paragraph('<b>Description:</b> Production-style pipeline for scraping, validating, and exporting structured datasets for AI training pipelines. Designed to align specifically with hybrid AI + human data production workflows.', p_style))
elements.append(Spacer(1, 15))

elements.append(Paragraph('<b>Key Features:</b>', p_style))
elements.append(Spacer(1, 5))
elements.append(Paragraph('• <b>Dynamic Scraping (JS Handling):</b> Reliable extraction from dynamic web sources using Selenium and headless Chrome, effectively navigating JavaScript-rendered content and handling asynchronous loads.', p_style))
elements.append(Spacer(1, 5))
elements.append(Paragraph('• <b>Validation Layer:</b> Enforces data quality standards through robust schema validation, cross-source consistency controls, format verification, and automated null-value detection.', p_style))
elements.append(Spacer(1, 5))
elements.append(Paragraph('• <b>Batch Processing:</b> Scales scraping operations for large datasets using efficient batching mechanisms, complete with parallelized request tracking and automated retry logic with exponential backoff.', p_style))
elements.append(Spacer(1, 5))
elements.append(Paragraph('• <b>Extensive Exporting:</b> Delivers high-quality datasets in well-structured formats including CSV, JSON, and direct-to-Google Sheets pipeline integration.', p_style))
elements.append(Spacer(1, 5))
elements.append(Paragraph('• <b>AI Integration (OpenRouter):</b> Leverages internal LLM APIs for automated data cleaning, structural normalization, text artifact removal, and dynamic quality scoring.', p_style))

doc.build(elements)

print(f"PDF successfully generated at {pdf_path}")
