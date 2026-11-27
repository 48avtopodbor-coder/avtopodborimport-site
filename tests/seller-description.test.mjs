import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import ts from "typescript";

const directory = path.dirname(fileURLToPath(import.meta.url));
const source = fs.readFileSync(path.join(directory, "../src/lib/seller-description.ts"), "utf8");
const javascript = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, esModuleInterop: true },
}).outputText;
const compiled = { exports: {} };
const requireForSource = createRequire(path.join(directory, "../src/lib/seller-description.ts"));
new Function("module", "exports", "require", javascript)(
  compiled,
  compiled.exports,
  requireForSource,
);
const { sellerDescription } = compiled.exports;

test("переводит смешанное объявление целиком и сохраняет условия продавца", () => {
  const result = sellerDescription(
    "Здравствуйте!Мы—профессиональнаякомпанияпоэкспортуавтомобилей.Всеавтомобилиявляютсянашимсобственнымтоваром.Есливасзаинтересуетэтотавтомобиль，свяжитесьснами，мыможемдоставитьеговуказанноевамиместо.原版原漆！支持任何第三方检测！！欢迎下单验车！全国物流！Hello，boss.Ifyouareinterestedinthiscar，pleasecontactmeintime.Wecansendittoyourlocation",
  );
  assert.equal(result.dictionary, true);
  assert.doesNotMatch(result.text, /экспортом автомобилей|свяжитесь|hello.*boss/i);
  assert.match(result.text, /краска заводская/);
  assert.match(result.text, /сторонняя проверка/);
  assert.match(result.text, /доставка по Китаю/);
});

test("сохраняет суммы и дополнительные платежи продавца", () => {
  const result = sellerDescription(
    "【澳康达简介】车辆售价=车源展示车价加整备服务费加一年质保费（含保养），整备服务费为车价2%（不低于5000元），一年质保费为车价2%或3%（不低于3650元，不超过50000元），具体与销售顾问了解详情。澳康达，始创于1999年，是中国二手车领军企业品牌。26载专注实业经营，澳康达坚定践行“自有品牌、自建展厅、自主经营”的实体发展模式，以匠心品质和口碑服务，建立标杆品牌，累计服务客户超过30万。澳康达（深圳）名车广场，是澳康达建立的全球首座定制化名车综合体，总面积12万㎡、6层立体展厅，创下吉尼斯世界纪录：全球最大二手车交易展厅。澳康达（上海）名车广场，位于上海大虹桥商务区，于2023年2月启动营业，总面积12万㎡，5层立体展厅，为长三角汽车爱好者带来全新二手名车体验。澳康达（成都）名车广场于2024年3月亮相成都国际空港商务区，总建面约12万㎡，5层立体展厅，刷新西南消费者对二手车的认知。澳康达（天津）名车广场，于2024年8月在天津武清区正式开业，总面积12万㎡、4层立体展厅，成为华北最大二手车交易地标。作为二手车标杆品牌，澳康达始终秉持认真做好二手车的理念，每一台澳康达认证车，都要进行八大类360项检测和整备环节以确保车辆的品质，售后分品牌提供专业服务及质保服务，包括7天无理由退车、1年不限公里质保和免费保养、终身免费车辆年检、24小时道路救援等，让消费者用车无忧",
  );
  assert.equal(result.dictionary, true);
  assert.match(result.text, /5 000 юаней/);
  assert.match(result.text, /3 650/);
  assert.match(result.text, /50 000/);
  assert.match(result.text, /2% или 3%/);
});

test("сохраняет ограничение продавца на обращения по экспорту", () => {
  const result = sellerDescription(
    "出口外贸勿扰！！！同行勿扰！！！公司承诺所发车源真实，实车拍摄.手续合法齐全.[品质保障]我司所售车辆，手续及证件齐全，正规合法。发布车辆照片均为实车拍摄，车辆还可到任何专业机构和4S店进行车况检测。保证无重大事故、无火烧、无水泡。欲了解更多车辆详细信息请亲临我公司；欢迎您到现场看车、试车，我们将热情期待您的光临！此外我们还提供二手车按揭业务，利息低廉，方便快捷，可办理首付，**低三成，时间**长三年的按揭业务。相信有一次的合作，我们将成为永远的朋友！",
  );
  assert.equal(result.dictionary, true);
  assert.match(result.text, /не обращаться экспортёров/);
  assert.match(result.text, /30%/);
});

test("сохраняет предупреждение о неподтверждённом пробеге", () => {
  const result = sellerDescription("原漆，不保实表");
  assert.equal(result.dictionary, true);
  assert.match(result.text, /пробега продавец не гарантирует/);
});

test("не теряет сведения о ДТП и изменённом пробеге", () => {
  const result = sellerDescription("此车为事故车 调表车");
  assert.match(result.text, /после ДТП/);
  assert.match(result.text, /пробега изменены/);
});

test("переводит набор знакомых фраз только целиком", () => {
  assert.equal(sellerDescription("原漆，无事故，无火烧").dictionary, true);
  assert.equal(sellerDescription("原漆，无事故，发动机损坏").translated, false);
  assert.equal(sellerDescription("无事故，但已维修").translated, false);
});

test("оставляет неизвестный оригинал целым", () => {
  const original = "【车况】\n右后门喷漆";
  assert.deepEqual(sellerDescription(original), {
    text: original,
    translated: false,
    dictionary: false,
  });
  assert.equal(sellerDescription(null), null);
  assert.equal(sellerDescription("   "), null);
  assert.equal(sellerDescription("__proto__").text, "__proto__");
});

test("сохраняет следы окраски и среднюю оценку состояния в частом шаблоне", () => {
  const original =
    "外观：漆面保养良好，车身结构无修复，无重大事故。内饰：干净整洁。安全指示灯正常，气囊等被动安全项正常，车辆内电子器件使用良好，车内静态动态设备完善。驾驶：车辆点火、起步、提速、过弯、减速、制动均无问题，加速迅猛，动力输出平稳舒适,无怠速抖动。整体：整体车况一般。车体骨架结构无变形扭曲、无火烧泡水痕迹。车身有喷漆痕迹，整体漆面良好，排除大事故车辆。视野宽阔，练手选择，空间宽敞明亮通风性好，适合家庭代步车。";
  const result = sellerDescription(original);
  assert.equal(result.dictionary, true);
  assert.match(result.text, /следы окраски/);
  assert.match(result.text, /как среднее/);
});

test("очищает публичный текст и сохраняет факты об автомобиле", () => {
  const cases = JSON.parse(fs.readFileSync(path.join(directory, "seller-content-cases.json"), "utf8"));
  for (const [source, facts, removed] of cases) {
    const publicText = compiled.exports.cleanSellerText(source);
    for (const fact of facts) assert.ok(publicText.includes(fact), fact);
    for (const contact of removed) assert.ok(!publicText.includes(contact), contact);
    assert.equal(compiled.exports.cleanSellerText(publicText), publicText);
  }
});
