<available_skills>
  <skill>
    <name>calculator</name>
    <description>执行基本数学计算。触发词：计算、算一下、加法、减法、乘法、除法、平方、开方。</description>
    <location>./backend/skills/calculator/SKILL.md</location>
  </skill>
  <skill>
    <name>docx</name>
    <description>Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files). Triggers include: any mention of "Word doc", "word document", ".docx", or requests to produce professional documents with formatting like tables of contents, headings, page numbers, or letterheads. Also use when extracting or reorganizing content from .docx files, inserting or replacing images in documents, performing find-and-replace in Word files, working with tracked changes or comments, or converting content into a polished Word document. If the user asks for a "report", "memo", "letter", "template", or similar deliverable as a Word or .docx file, use this skill. Do NOT use for PDFs, spreadsheets, Google Docs, or general coding tasks unrelated to document generation.</description>
    <location>./backend/skills/docx/SKILL.md</location>
  </skill>
  <skill>
    <name>get_weather</name>
    <description>获取指定城市的实时天气信息</description>
    <location>./backend/skills/get_weather/SKILL.md</location>
  </skill>
  <skill>
    <name>long_document_workflow</name>
    <description>Use when user requests to generate a long document with specific topic and format. This skill provides a structured workflow for creating well-organized, multi-section documents with consistent formatting.</description>
    <location>./backend/skills/long_document_workflow/SKILL.md</location>
  </skill>
  <skill>
    <name>pptx</name>
    <description>Use this skill any time a .pptx file is involved in any way — as input, output, or both. This includes: creating slide decks, pitch decks, or presentations; reading, parsing, or extracting text from any .pptx file (even if the extracted content will be used elsewhere, like in an email or summary); editing, modifying, or updating existing presentations; combining or splitting slide files; working with templates, layouts, speaker notes, or comments. Trigger whenever the user mentions "deck," "slides," "presentation," or references a .pptx filename, regardless of what they plan to do with the content afterward. If a .pptx file needs to be opened, created, or touched, use this skill.</description>
    <location>./backend/skills/pptx/SKILL.md</location>
  </skill>
</available_skills>