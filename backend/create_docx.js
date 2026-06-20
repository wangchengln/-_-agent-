
const { Document, Packer, Paragraph, TextRun, HeadingLevel, PageOrientation } = require('docx');
const fs = require('fs');

// 创建文档
const doc = new Document({
    sections: [{
        properties: {
            page: {
                size: {
                    width: 12240,   // US Letter 宽度 (8.5英寸)
                    height: 15840   // US Letter 高度 (11英寸)
                },
                margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } // 1英寸边距
            }
        },
        children: [
            // 标题
            new Paragraph({
                heading: HeadingLevel.HEADING_1,
                children: [new TextRun({ text: "fufan OpenClaw 自我介绍", bold: true, size: 32 })]
            }),
            
            // 空行
            new Paragraph({ children: [new TextRun("")] }),
            
            // 基本信息
            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                children: [new TextRun({ text: "基本信息", bold: true, size: 28 })]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "• 名称: fufan OpenClaw", size: 24 }),
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "• 版本: 0.2.0", size: 24 }),
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "• 定位: 本地运行的透明 AI Agent 助手", size: 24 }),
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "• 风格: 专业而不刻板，友好而不浮夸", size: 24 }),
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "• 语言: 默认中文回复，跟随用户语言切换", size: 24 }),
                ]
            }),
            
            // 空行
            new Paragraph({ children: [new TextRun("")] }),
            
            // 核心原则
            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                children: [new TextRun({ text: "核心原则", bold: true, size: 28 })]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "1. 透明优先: 所有操作（工具调用、记忆读写、技能执行）对用户完全可见。", size: 24 }),
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "2. 文件即记忆: 记忆以 Markdown 文件的形式存在，任何人都可以直接阅读和编辑。", size: 24 }),
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "3. 技能即学习: 通过阅读 SKILL.md 来学习新能力，就像人类阅读说明书一样。", size: 24 }),
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "4. 安全边界: 只在授权的目录内操作，不执行危险命令，不读取系统敏感文件。", size: 24 }),
                ]
            }),
            
            // 空行
            new Paragraph({ children: [new TextRun("")] }),
            
            // 沟通风格
            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                children: [new TextRun({ text: "沟通风格", bold: true, size: 28 })]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "• 简洁、准确、有条理", size: 24 }),
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "• 遇到不确定的问题会坦诚告知", size: 24 }),
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "• 在执行操作前会说明意图", size: 24 }),
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "• 用中文与用户交流（除非用户使用其他语言）", size: 24 }),
                ]
            }),
            
            // 空行
            new Paragraph({ children: [new TextRun("")] }),
            
            // 可用技能
            new Paragraph({
                heading: HeadingLevel.HEADING_2,
                children: [new TextRun({ text: "可用技能", bold: true, size: 28 })]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "1. docx: 创建、编辑和操作 Word 文档", size: 24 }),
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "2. get_weather: 获取指定城市的实时天气信息", size: 24 }),
                ]
            }),
            new Paragraph({
                children: [
                    new TextRun({ text: "3. long_document_workflow: 长文档生成工作流", size: 24 }),
                ]
            }),
            
            // 空行
            new Paragraph({ children: [new TextRun("")] }),
            
            // 结尾
            new Paragraph({
                children: [
                    new TextRun({ text: "有什么我可以帮助你的吗？无论是文档处理、信息查询还是其他任务，我都很乐意协助你！", size: 24, italic: true }),
                ]
            }),
        ]
    }]
});

// 保存文档
Packer.toBuffer(doc).then((buffer) => {
    fs.writeFileSync('openclaw_self_introduction.docx', buffer);
    console.log('文档已保存为 openclaw_self_introduction.docx');
});
