import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const route = ts.transpileModule(
  fs.readFileSync(new URL("../src/app/api/img/route.ts", import.meta.url), "utf8"),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } },
).outputText;
const maxBytes = 20 * 1024 * 1024;

function requestImage(fetch, url = "https://2sc2.autoimg.cn/photo.webp") {
  const exports = {};
  vm.runInNewContext(route, {
    exports,
    fetch,
    URL,
    AbortSignal,
    Uint8Array,
    require: () => ({ NextResponse: Response }),
  });
  const nextUrl = new URL("https://avtopodborimport.ru/api/img");
  nextUrl.searchParams.set("url", url);
  return exports.GET({ nextUrl, signal: new AbortController().signal });
}

test("the fallback forwards image content and prevents automatic redirects", async () => {
  const bytes = new Uint8Array([1, 2, 3]);
  const result = await requestImage((url, options) => {
    assert.equal(url.hostname, "2sc2.autoimg.cn");
    assert.equal(options.redirect, "error");
    return new Response(bytes, { headers: { "Content-Type": "image/webp" } });
  });
  assert.equal(result.status, 200);
  assert.equal(result.headers.get("Content-Type"), "image/webp");
  assert.deepEqual(new Uint8Array(await result.arrayBuffer()), bytes);
});

test("the fallback rejects non-image and active image content", async () => {
  for (const type of ["text/html", "image/svg+xml", ""]) {
    const result = await requestImage(
      () =>
        new Response(new Uint8Array([0]), {
          headers: { "Content-Type": type },
        }),
    );
    assert.equal(result.status, 415);
  }
});

test("the fallback limits bytes both with and without a declared size", async () => {
  const declared = await requestImage(
    () =>
      new Response("oversize", {
        headers: { "Content-Type": "image/jpeg", "Content-Length": String(maxBytes + 1) },
      }),
  );
  assert.equal(declared.status, 413);

  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(new Uint8Array(maxBytes));
      controller.enqueue(new Uint8Array([0]));
      controller.close();
    },
  });
  const streamed = await requestImage(
    () =>
      new Response(stream, {
        headers: { "Content-Type": "image/jpeg" },
      }),
  );
  assert.equal(streamed.status, 413);
});
