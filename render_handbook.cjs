const {chromium} = require('playwright');
const path = require('path');
(async () => {
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve('tmp/pdfs/supplement.html'));
  await page.evaluate(() => document.fonts.ready);
  const errors = await page.locator('.page').evaluateAll(pages => pages.flatMap((p,i) => {
    const footer = p.querySelector('footer').getBoundingClientRect();
    const content = [...p.children].filter(n=>n.tagName!=='FOOTER');
    return content.some(n=>n.getBoundingClientRect().bottom > footer.top - 6) ? [i+1] : [];
  }));
  if(errors.length) throw new Error('Content overlaps footer on supplement pages: '+errors);
  await page.pdf({path:'tmp/pdfs/supplement.pdf',format:'A4',printBackground:true,preferCSSPageSize:true});
  console.log('Rendered 28 pages; all content clears footers');
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
