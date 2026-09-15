content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('id="newsDiscussionModal"')
print(content[p:p+1200].encode('ascii', errors='replace').decode())

