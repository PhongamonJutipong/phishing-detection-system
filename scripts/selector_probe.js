/**
 * สำรวจ selector ของหน้าเว็บอีเมล เพื่อนำไปเติมในตาราง PROVIDERS ที่ extension/providers.js
 *
 * วิธีใช้
 *   1. เปิดอ่านอีเมล "สักฉบับหนึ่ง" ในเว็บของผู้ให้บริการที่ต้องการเพิ่ม
 *      (ต้องเปิดอ่านจริง ไม่ใช่ค้างอยู่ที่หน้ารายการ ไม่งั้นจะไม่เจอกล่องเนื้อหา)
 *   2. กด F12 เปิด DevTools แล้วไปแท็บ Console
 *   3. คัดลอกไฟล์นี้ทั้งไฟล์ไปวางแล้วกด Enter
 *   4. นำผลที่ได้มาแก้ค่าในตาราง PROVIDERS
 *
 * สคริปต์นี้อ่านอย่างเดียว ไม่แก้หน้าเว็บ ไม่ส่งข้อมูลออกไปไหน
 * และไม่พิมพ์เนื้อหาอีเมลออกมา พิมพ์แค่ความยาวกับ selector ที่ใช้ได้
 */
(function probe() {
  const CANDIDATES = {
    body: [
      "div.a3s",
      "#UniqueMessageBody",
      'div[role="document"]',
      "div.allowTextSelection",
      'div[aria-label][role="region"]',
    ],
    subject: [
      "h2.hP",
      'div[role="heading"][aria-level="2"]',
      'span[role="heading"]',
      "h1",
      "h2",
    ],
    sender: [
      "span.gD",
      'span[title*="@"]',
      'button[title*="@"]',
      'a[href^="mailto:"]',
    ],
    message: [
      "div.adn",
      'div[role="main"]',
      'div[role="listitem"]',
      "article",
    ],
  };

  /** ตัวที่ "มองเห็นอยู่จริง" เท่านั้นถึงจะนับ เพราะหน้าอีเมลซ่อน element ทิ้งไว้เยอะมาก */
  const visible = (el) => el.offsetParent !== null && el.innerText && el.innerText.trim().length > 0;

  console.log("%cselector probe", "font-weight:bold;font-size:14px");
  console.log("host:", location.hostname);

  const chosen = {};
  for (const [role, selectors] of Object.entries(CANDIDATES)) {
    const rows = [];
    for (const sel of selectors) {
      let nodes = [];
      try {
        nodes = [...document.querySelectorAll(sel)].filter(visible);
      } catch (err) {
        rows.push({ selector: sel, พบ: "selector ไม่ถูกต้อง" });
        continue;
      }
      if (!nodes.length) continue;
      const longest = nodes.reduce((a, b) => (a.innerText.length >= b.innerText.length ? a : b));
      rows.push({
        selector: sel,
        จำนวน: nodes.length,
        ตัวอักษรมากสุด: longest.innerText.trim().length,
      });
      if (!chosen[role]) chosen[role] = sel;
    }
    console.log(`\n--- ${role} ---`);
    if (rows.length) console.table(rows);
    else console.log("ไม่เจอเลย ต้องหา selector เองด้วยการคลิกขวาที่ element แล้วกด Inspect");
  }

  console.log("\n--- สรุป: นำไปวางใน extension/providers.js ---");
  console.log(JSON.stringify(chosen, null, 2));

  // ตรวจ Shadow DOM: ถ้าหน้านี้ซ่อนเนื้อหาไว้ใน shadow root
  // querySelectorAll ธรรมดาจะเจาะไม่ถึง ต้องออกแบบ adapter ต่างออกไป
  const shadowHosts = [...document.querySelectorAll("*")].filter((el) => el.shadowRoot).length;
  console.log(`\nshadow root ในหน้านี้: ${shadowHosts} จุด`);
  if (shadowHosts > 0) {
    console.warn(
      "หน้านี้ใช้ Shadow DOM ถ้าหา body ไม่เจอด้านบน แปลว่าเนื้อหาน่าจะอยู่ใน shadow root " +
        "ซึ่ง querySelectorAll เจาะไม่ได้ ต้องเพิ่มวิธีอ่านแบบอื่นใน providers.js"
    );
  }
})();
