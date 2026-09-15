import zipfile

with zipfile.ZipFile(r'c:\Users\SantoshMadnani\Documents\CA_Trader\42.zip') as z:
    text = z.read('terminal.html').decode('utf-8', errors='ignore')

p_summary = text.find('id="masterSummaryCard"')
p_banner = text.find('id="chartRecoBanner"')
p_evidence = text.find('id="chartRecoEvidenceSection"')
p_shell = text.find('id="chartShell"')

print(f"masterSummaryCard: {p_summary}")
print(f"chartRecoBanner: {p_banner}")
print(f"chartRecoEvidenceSection: {p_evidence}")
print(f"chartShell: {p_shell}")

# In 42.zip, the entire block to shift to Dashboard is from masterSummaryCard to chartShell!
chunk_to_dashboard = text[text.rfind('<div', 0, p_summary):text.rfind('<div', 0, p_shell)]
print("Chunk length:", len(chunk_to_dashboard))
print("Starts with:", repr(chunk_to_dashboard[:80]))
print("Ends with:", repr(chunk_to_dashboard[-80:]))

