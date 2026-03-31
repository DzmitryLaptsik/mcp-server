const path = require('path');
const pptxgen = require(path.join(process.env.HOME, '.agents/skills/pptx/node_modules/pptxgenjs'));
const html2pptx = require(path.join(process.env.HOME, '.agents/skills/pptx/scripts/html2pptx'));

async function build() {
    const pptx = new pptxgen();
    pptx.layout = 'LAYOUT_16x9';
    pptx.author = 'MCP Assistant Team';
    pptx.title = 'MCP Assistant - Personal Productivity Server';

    const slides = [
        'slides/slide1-title.html',
        'slides/slide2-overview.html',
        'slides/slide3-tools.html',
        'slides/slide4-architecture.html',
        'slides/slide5-ui-login.html',
        'slides/slide6-ui-chat.html',
        'slides/slide7-techstack.html',
        'slides/slide8-security.html',
        'slides/slide9-thankyou.html',
    ];

    for (const htmlFile of slides) {
        const fullPath = path.join(__dirname, htmlFile);
        console.log(`Processing: ${htmlFile}`);
        await html2pptx(fullPath, pptx);
    }

    const outPath = path.join(__dirname, 'MCP-Assistant-Presentation.pptx');
    await pptx.writeFile({ fileName: outPath });
    console.log(`Presentation saved: ${outPath}`);
}

build().catch(err => { console.error(err); process.exit(1); });
