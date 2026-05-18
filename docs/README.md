# LED Matrix — Web Showcase

The single-page visual showcase for the LED Matrix project, deployed via GitHub Pages and embedded into [yinglianliu.com/portfolio/glowing-cells](https://www.yinglianliu.com/portfolio/glowing-cells).

## Files

| File | Use |
|---|---|
| `index.html` | **Embed version** — for Squarespace iframe. No nav/footer; auto-reports its height to parent. |
| `standalone.html` | **Full version** — with its own nav + footer, for direct viewing. |

## Live URL

After GitHub Pages is enabled, this folder is served at:

> **https://yinglianliu.github.io/LEDMatrixTDPi/**

- `https://yinglianliu.github.io/LEDMatrixTDPi/` → embed version (index.html)
- `https://yinglianliu.github.io/LEDMatrixTDPi/standalone.html` → standalone version

---

## Deployment — one-time setup

```bash
# from your local clone of LEDMatrixTDPi
# (drop the docs/ folder into the repo root first)
git add docs/
git commit -m "Add web showcase page"
git push
```

Then on GitHub:

1. Open **Settings → Pages** ([direct link](https://github.com/yinglianliu/LEDMatrixTDPi/settings/pages))
2. **Source**: `Deploy from a branch`
3. **Branch**: `main`  ·  **Folder**: `/docs`
4. Save — Pages goes live in ~1 min

---

## Squarespace embed snippet

After Pages is live, paste this into a **Code Block** on the Glowing Cells page (replaces the old description + Vimeo block):

```html
<iframe
  id="led-matrix-frame"
  src="https://yinglianliu.github.io/LEDMatrixTDPi/"
  style="width:100%;height:9800px;border:0;display:block;background:#070708;border-radius:6px"
  loading="lazy"
  allow="autoplay; fullscreen; picture-in-picture"
  title="LED Matrix — project showcase">
</iframe>
<script>
// Auto-resize: the embed posts its real height — apply it so there's no extra whitespace.
window.addEventListener('message', function(e){
  if (e.data && e.data.type === 'led-matrix-embed-height'){
    var f = document.getElementById('led-matrix-frame');
    if (f) f.style.height = e.data.height + 'px';
  }
});
</script>
```

> If your Squarespace plan strips inline `<script>` (some Personal plans do), keep `height:9800px` fixed and remove the `<script>` tag — page caps at ~9700 px at desktop width.

---

## Notes

- Both files are fully self-contained — only external requests are Google Fonts + Vimeo
- Vimeo player is themed with the LED orange (`#ff7a3a`)
- Mobile responsive — collapses to single column under 980 px
