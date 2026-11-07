/* Furnished 3D viewer for a design model (conceptdesign).
   Plan metres: x east, y north, z level. three.js: Y up, north = -Z.
   Each level can be shown on its own as a cutaway (walls cut at 2.4 m; the walls facing the
   camera drop to 0.6 m), or the whole building with its roof and site. Furniture is built here
   from simple rounded shapes; positions come from the design model. Renders only on change. */
(function () {
  "use strict";
  var S = window.SCENE;
  if (THREE.ColorManagement) THREE.ColorManagement.legacyMode = false;
  var CX = S.center[0], CY = S.center[1];
  function P(x, y, z) { return new THREE.Vector3(x - CX, z, CY - y); }
  var V = function (x, y, z) { return new THREE.Vector3(x, y, z); };
  var Q0 = new THREE.Quaternion();
  var STILL = /still/.test(location.hash);
  if (STILL) document.body.classList.add("still");

  // ------------------------------------------------------------------ renderer, scene, camera
  var view = document.getElementById("view");
  var W = function () { return window.innerWidth; }, H = function () { return window.innerHeight; };
  var renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, STILL ? 1 : 1.5));
  renderer.setSize(W(), H());
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  view.appendChild(renderer.domElement);

  var labelRenderer = new THREE.CSS2DRenderer();
  labelRenderer.setSize(W(), H());
  labelRenderer.domElement.className = "labels";
  view.appendChild(labelRenderer.domElement);

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(30, W() / H(), 0.5, 400);
  var controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.minDistance = 3;
  controls.maxDistance = 120;

  var hemi = new THREE.HemisphereLight(0xffffff, 0xd9d2c6, 0.62);
  var amb = new THREE.AmbientLight(0xffffff, 0.16);
  var sun = new THREE.DirectionalLight(0xfff4e6, 1.35);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.bias = -0.0003;
  sun.shadow.normalBias = 0.015;
  scene.add(hemi, amb, sun, sun.target);

  // ------------------------------------------------------------------ textures (drawn here)
  var seed = 11;
  function rnd() { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }
  var ANISO = renderer.capabilities.getMaxAnisotropy();
  function canvasTex(size, metres, draw, color) {
    var c = document.createElement("canvas");
    c.width = c.height = size;
    draw(c.getContext("2d"), size);
    var t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    if (color !== false) t.encoding = THREE.sRGBEncoding;
    t.anisotropy = ANISO;
    t.userData.metres = metres;
    return t;
  }
  function hsl(h, s, l, a) { return "hsla(" + h + "," + s + "%," + l + "%," + (a == null ? 1 : a) + ")"; }

  // boards running along x; each row wraps so the texture tiles without seams
  function boards(rows, hue, sat, light, jitter, joint) {
    return function (g, n) {
      var h = n / rows;
      for (var r = 0; r < rows; r++) {
        var lens = [], sum = 0;
        while (sum < n) { var L = n * (0.28 + rnd() * 0.42); lens.push(L); sum += L; }
        var k = n / sum, x = rnd() * n;
        lens.forEach(function (L) {
          L *= k;
          var col = hsl(hue + (rnd() - 0.5) * 6, sat + (rnd() - 0.5) * 8, light + (rnd() - 0.5) * jitter);
          for (var rep = -1; rep <= 0; rep++) {
            var x0 = x + rep * n;
            g.fillStyle = col;
            g.fillRect(x0, r * h, L, h);
            for (var q = 0; q < 16; q++) {
              var yy = r * h + 2 + rnd() * (h - 4), wob = (rnd() - 0.5) * 5;
              g.strokeStyle = "rgba(70,45,20," + (0.03 + rnd() * 0.07) + ")";
              g.lineWidth = 0.6 + rnd() * 1.4;
              g.beginPath();
              g.moveTo(x0, yy);
              g.bezierCurveTo(x0 + L * 0.3, yy + wob, x0 + L * 0.7, yy - wob, x0 + L, yy + wob * 0.4);
              g.stroke();
            }
            g.fillStyle = joint;
            g.fillRect(x0 + L - 1.5, r * h, 1.5, h);
          }
          x += L;
          if (x > n) x -= n;
        });
        g.fillStyle = joint;
        g.fillRect(0, r * h, n, 1.5);
      }
    };
  }
  function tiles(count, base, grout, mottle) {
    return function (g, n) {
      var s = n / count;
      g.fillStyle = grout;
      g.fillRect(0, 0, n, n);
      for (var i = 0; i < count; i++) for (var j = 0; j < count; j++) {
        g.fillStyle = hsl(base[0], base[1], base[2] + (rnd() - 0.5) * 3);
        g.fillRect(i * s + 1.5, j * s + 1.5, s - 3, s - 3);
        for (var q = 0; q < mottle; q++) {
          g.fillStyle = "rgba(" + (rnd() < 0.5 ? "255,255,255," : "90,80,70,") + (rnd() * 0.05) + ")";
          var rr = 2 + rnd() * 14;
          g.beginPath();
          g.arc(i * s + 2 + rnd() * (s - 4), j * s + 2 + rnd() * (s - 4), rr, 0, 7);
          g.fill();
        }
      }
    };
  }
  function noise(base, spread, dots, size) {
    return function (g, n) {
      g.fillStyle = base;
      g.fillRect(0, 0, n, n);
      for (var q = 0; q < dots; q++) {
        var c = spread[Math.floor(rnd() * spread.length)];
        g.fillStyle = c;
        var r = size * (0.3 + rnd());
        g.beginPath();
        g.arc(rnd() * n, rnd() * n, r, 0, 7);
        g.fill();
      }
    };
  }
  function ashlar(g, n) {
    g.fillStyle = "#6f6a62";
    g.fillRect(0, 0, n, n);
    var rows = 7, h = n / rows;
    for (var r = 0; r < rows; r++) {
      var x = -rnd() * 60;
      while (x < n) {
        var L = 50 + rnd() * 90;
        var l = 58 + rnd() * 14, hue = 30 + rnd() * 14, sat = 6 + rnd() * 9;
        g.fillStyle = hsl(hue, sat, l);
        g.fillRect(x + 2, r * h + 2, L - 4, h - 4);
        g.fillStyle = "rgba(255,255,255,0.06)";
        g.fillRect(x + 2, r * h + 2, L - 4, 3);
        x += L;
      }
    }
  }
  function cladding(g, n) {
    var cols = 10, w = n / cols;
    for (var i = 0; i < cols; i++) {
      g.fillStyle = hsl(26 + rnd() * 6, 42 + rnd() * 8, 42 + rnd() * 7);
      g.fillRect(i * w, 0, w, n);
      for (var q = 0; q < 10; q++) {
        g.strokeStyle = "rgba(50,30,15," + (0.05 + rnd() * 0.08) + ")";
        g.lineWidth = 1;
        var xx = i * w + 2 + rnd() * (w - 4);
        g.beginPath(); g.moveTo(xx, 0); g.lineTo(xx + (rnd() - 0.5) * 4, n); g.stroke();
      }
      g.fillStyle = "rgba(30,20,10,0.55)";
      g.fillRect(i * w + w - 2, 0, 2, n);
    }
  }

  function brick(g, n) {
    g.fillStyle = "#cfc6b8";
    g.fillRect(0, 0, n, n);
    var rows = 16, h = n / rows, L = n / 4;
    for (var r = 0; r < rows; r++) {
      for (var x = -(r % 2) * L / 2; x < n; x += L) {
        g.fillStyle = hsl(12 + rnd() * 10, 36 + rnd() * 14, 40 + rnd() * 9);
        g.fillRect(x + 2, r * h + 2, L - 4, h - 3);
      }
    }
  }

  var TEX = {
    wood: canvasTex(1024, 1.6, boards(8, 31, 40, 63, 9, "rgba(70,45,22,0.45)")),
    deck: canvasTex(512, 1.4, boards(10, 25, 35, 40, 8, "rgba(30,20,10,0.7)")),
    tile: canvasTex(512, 1.2, tiles(2, [40, 6, 86], "#b9b6b0", 40)),
    stone: canvasTex(512, 1.6, tiles(2, [36, 14, 83], "#c2b9aa", 70)),
    concrete: canvasTex(256, 2.0, noise("#bdbab4", ["rgba(255,255,255,0.05)", "rgba(80,75,70,0.06)"], 900, 6)),
    pave: canvasTex(512, 1.2, tiles(3, [38, 10, 79], "#a8a297", 25)),
    grass: canvasTex(256, 4.0, noise("#86a35f", ["rgba(60,95,40,0.25)", "rgba(150,175,90,0.25)",
      "rgba(110,130,60,0.3)"], 2600, 3)),
    ashlar: canvasTex(512, 2.0, ashlar),
    earth: canvasTex(256, 1.5, noise("#a48e72", ["rgba(70,50,30,0.25)", "rgba(190,170,140,0.25)",
      "rgba(120,100,75,0.3)"], 1800, 3)),
    cladding: canvasTex(512, 1.2, cladding),
    brick: canvasTex(512, 1.0, brick)
  };

  function aoCanvas() {           // dark at the top edge, fading out
    var c = document.createElement("canvas");
    c.width = 4; c.height = 64;
    var g = c.getContext("2d");
    for (var y = 0; y < 64; y++) {
      var t = y / 63;
      g.fillStyle = "rgba(0,0,0," + (0.42 * Math.pow(1 - t, 2.2)) + ")";
      g.fillRect(0, y, 4, 1);
    }
    return new THREE.CanvasTexture(c);
  }
  function blobCanvas() {         // soft rounded rectangle for contact shadows
    var c = document.createElement("canvas");
    c.width = c.height = 128;
    var g = c.getContext("2d");
    g.filter = "blur(9px)";
    g.fillStyle = "rgba(0,0,0,1)";
    g.fillRect(22, 22, 84, 84);
    return new THREE.CanvasTexture(c);
  }

  // ------------------------------------------------------------------ materials
  var M = {};
  function mat(name, color, o) {
    M[name] = new THREE.MeshStandardMaterial(Object.assign({ color: color, roughness: 0.85, metalness: 0 }, o || {}));
    return M[name];
  }
  function tmat(name, tex, o) {
    M[name] = new THREE.MeshStandardMaterial(Object.assign({ map: tex, roughness: 0.8, metalness: 0 }, o || {}));
    M[name].userData.metres = tex.userData.metres;
    return M[name];
  }
  mat("wall", 0xf3f1ed, { roughness: 0.95 });
  mat("render", 0xf0ede7, { roughness: 0.95 });
  mat("slab", 0xe6e3dd, { roughness: 0.95 });
  mat("slabedge", 0xebe8e2, { roughness: 0.95 });
  tmat("stone", TEX.ashlar, { roughness: 0.95 });
  tmat("stonewall", TEX.ashlar, { roughness: 0.95 });
  tmat("brick", TEX.brick, { roughness: 0.92 });
  tmat("cladding", TEX.cladding, { roughness: 0.75 });
  tmat("earth", TEX.earth, { roughness: 1.0 });
  tmat("wood", TEX.wood, { roughness: 0.62 });
  tmat("deck", TEX.deck, { roughness: 0.8 });
  tmat("tile", TEX.tile, { roughness: 0.35 });
  tmat("stonefloor", TEX.stone, { roughness: 0.45 });
  tmat("concrete", TEX.concrete, { roughness: 0.9 });
  tmat("pave", TEX.pave, { roughness: 0.9 });
  tmat("grass", TEX.grass, { roughness: 1.0 });
  M.glass = new THREE.MeshStandardMaterial({ color: 0xa8c9d8, roughness: 0.05, metalness: 0.1,
    transparent: true, opacity: 0.24, depthWrite: false });
  M.water = new THREE.MeshStandardMaterial({ color: 0x5fb8d8, roughness: 0.08, metalness: 0.05,
    transparent: true, opacity: 0.78, depthWrite: false });
  mat("frame", 0x2d3135, { roughness: 0.45, metalness: 0.35 });
  mat("door", 0xefebe5, { roughness: 0.6 });
  mat("doorwood", 0xa0703f, { roughness: 0.55 });
  mat("doorext", 0x3a3f44, { roughness: 0.5, metalness: 0.3 });
  mat("oak", 0xc59b6d, { roughness: 0.6 });
  mat("walnut", 0x6c4a33, { roughness: 0.55 });
  mat("lightwood", 0xd7bb92, { roughness: 0.6 });
  mat("steel", 0xa9afb5, { roughness: 0.35, metalness: 0.6 });
  mat("liftcab", 0xcfd2d5, { roughness: 0.4, metalness: 0.4 });
  mat("chrome", 0xe1e5e8, { roughness: 0.18, metalness: 0.9 });
  mat("road", 0x6c6f73, { roughness: 0.95 });
  mat("roof", 0x3b4046, { roughness: 0.55, metalness: 0.35 });
  mat("seam", 0x30353a, { roughness: 0.5, metalness: 0.4 });
  mat("bound", 0xddd6c8, { roughness: 0.95 });
  mat("cabinet", 0xf1eee9, { roughness: 0.45 });
  mat("worktop", 0x4c5055, { roughness: 0.3 });
  mat("quartz", 0xe9e6e0, { roughness: 0.3 });
  mat("black", 0x1f2124, { roughness: 0.5 });
  mat("screen", 0x101214, { roughness: 0.15, metalness: 0.2 });
  mat("seamline", 0xb9b5ae, { roughness: 0.7 });
  mat("ceramic", 0xfbfbf9, { roughness: 0.22 });
  mat("ceramicIn", 0xdfe2e3, { roughness: 0.2 });
  mat("mirror", 0xcdd7dd, { roughness: 0.04, metalness: 0.95 });
  mat("linen", 0xf8f6f1, { roughness: 0.95 });
  mat("duvetA", 0xa9b6c2, { roughness: 1.0 });
  mat("duvetB", 0xd8cdb8, { roughness: 1.0 });
  mat("throw", 0x6f7d89, { roughness: 1.0 });
  mat("headboard", 0xcfc6b8, { roughness: 1.0 });
  mat("bedbase", 0xdcd5ca, { roughness: 1.0 });
  mat("fabric", 0xd9d4cb, { roughness: 1.0 });
  mat("fabric2", 0xe4e0d8, { roughness: 1.0 });
  mat("fabricDark", 0x7e858c, { roughness: 1.0 });
  mat("cushionA", 0xb59f80, { roughness: 1.0 });
  mat("cushionB", 0x8d9ea9, { roughness: 1.0 });
  mat("cushionC", 0xc47f5b, { roughness: 1.0 });
  mat("leather", 0xa8714a, { roughness: 0.6 });
  mat("rugA", 0xdcd6cb, { roughness: 1.0 });
  mat("rugB", 0xbdb4a6, { roughness: 1.0 });
  mat("rugC", 0xa9b5bd, { roughness: 1.0 });
  mat("rugEdge", 0x8e877c, { roughness: 1.0 });
  mat("felt", 0x2e7a4d, { roughness: 1.0 });
  mat("sauna", 0xc99c68, { roughness: 0.75 });
  mat("saunaDark", 0x9d7148, { roughness: 0.75 });
  mat("tileWhite", 0xf1f1ef, { roughness: 0.3 });
  mat("appliance", 0xf4f4f2, { roughness: 0.35 });
  mat("carton", 0xc7a77a, { roughness: 0.95 });
  mat("binA", 0x8fa7b8, { roughness: 0.6 });
  mat("binB", 0xe2ddd3, { roughness: 0.6 });
  mat("copper", 0xb87348, { roughness: 0.35, metalness: 0.7 });
  mat("lamp", 0xf6efe2, { roughness: 0.8, emissive: 0x3a3022 });
  mat("pot1", 0xe8e4dc, { roughness: 0.7 });
  mat("pot2", 0x8f8b85, { roughness: 0.85 });
  mat("pot3", 0xb56f4c, { roughness: 0.85 });
  mat("soil", 0x4a3b2c, { roughness: 1.0 });
  mat("leaf1", 0x4f7f3f, { roughness: 0.9, flatShading: true });
  mat("leaf2", 0x6a9b4e, { roughness: 0.9, flatShading: true });
  mat("leaf3", 0x3f6a36, { roughness: 0.9, flatShading: true });
  mat("trunk", 0x6c4b30, { roughness: 1.0 });
  mat("conifer", 0x3b5f3c, { roughness: 0.9, flatShading: true });
  mat("carA", 0xbfc4ca, { roughness: 0.35, metalness: 0.55 });
  mat("carB", 0x2f4558, { roughness: 0.35, metalness: 0.55 });
  mat("carglass", 0x27313a, { roughness: 0.1, metalness: 0.3 });
  mat("tire", 0x1c1d1f, { roughness: 0.9 });
  mat("light", 0xfff8e8, { roughness: 0.3, emissive: 0x555044 });
  mat("taillight", 0xa0261f, { roughness: 0.3 });
  mat("umbrella", 0xeee8dc, { roughness: 1.0, side: THREE.DoubleSide });
  ["bottleG", 0x3d6b46, "bottleA", 0x9a5b22, "bottleC", 0xc9d6d8].forEach(function (v, i, a) {
    if (i % 2 === 0) mat(v, a[i + 1], { roughness: 0.15, metalness: 0.1 });
  });
  var CLOTHES = ["clothA", 0x3f4c5a, "clothB", 0xd8d2c6, "clothC", 0x9b6b52, "clothD", 0x6f8a7a,
                 "clothE", 0xf1efe9, "clothF", 0x2c2f33];
  for (var ci = 0; ci < CLOTHES.length; ci += 2) mat(CLOTHES[ci], CLOTHES[ci + 1], { roughness: 1.0 });
  var BOOKS = ["bookA", 0x8a3b32, "bookB", 0x2f5068, "bookC", 0xc9a85c, "bookD", 0x4e6b4a];
  for (ci = 0; ci < BOOKS.length; ci += 2) mat(BOOKS[ci], BOOKS[ci + 1], { roughness: 0.9 });
  // a soft studio made once and blurred, so metal, glass, mirrors and glossy tops reflect something
  (function () {
    var pmrem = new THREE.PMREMGenerator(renderer), env = new THREE.Scene();
    function panel(x, y, z, sx, sy, sz, c, back) {
      var m = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz),
        new THREE.MeshBasicMaterial({ color: c, side: back ? THREE.BackSide : THREE.FrontSide }));
      m.position.set(x, y, z);
      env.add(m);
    }
    panel(0, 4, 0, 24, 12, 24, 0xb3b0aa, true);
    panel(0, 9.8, 0, 12, 0.2, 12, 0xffffff);
    panel(-11.5, 5, 0, 0.2, 6, 14, 0xe6e6e6);
    panel(11.5, 4, 4, 0.2, 4, 8, 0xcfcfcf);
    panel(0, -1.9, 0, 24, 0.2, 24, 0x5f5a53);
    var tex = pmrem.fromScene(env, 0.035).texture;
    pmrem.dispose();
    [["chrome", 1.0], ["steel", 0.9], ["mirror", 1.0], ["glass", 1.0], ["water", 0.9], ["carglass", 1.0],
     ["screen", 0.8], ["ceramic", 0.55], ["ceramicIn", 0.5], ["frame", 0.6], ["liftcab", 0.8], ["worktop", 0.5],
     ["quartz", 0.45], ["roof", 0.5], ["appliance", 0.5], ["carA", 0.9], ["carB", 0.9], ["tileWhite", 0.4],
     ["copper", 0.9], ["tile", 0.35], ["stonefloor", 0.3], ["bottleG", 0.8], ["bottleA", 0.8], ["bottleC", 0.8],
     ["seam", 0.5], ["doorext", 0.5]].forEach(function (p) {
      M[p[0]].envMap = tex;
      M[p[0]].envMapIntensity = p[1];
      M[p[0]].needsUpdate = true;
    });
    M.mirror.color.set(0xdde5ea);
    M.mirror.metalness = 0.55;
    M.mirror.roughness = 0.12;
  })();
  var aoTex = aoCanvas(), blobTex = blobCanvas();
  M.ao = new THREE.MeshBasicMaterial({ map: aoTex, transparent: true, depthWrite: false, toneMapped: false,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
  M.blob = new THREE.MeshBasicMaterial({ map: blobTex, transparent: true, depthWrite: false, toneMapped: false,
    opacity: 0.38, polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3 });
  M.blobLight = M.blob.clone();
  M.blobLight.opacity = 0.2;
  var FLOOR_MAT = { wood: "wood", tile: "tile", stone: "stonefloor", deck: "deck", concrete: "concrete" };
  [M.wood, M.tile, M.stonefloor, M.deck, M.concrete].forEach(function (m) {
    m.polygonOffset = true; m.polygonOffsetFactor = -1; m.polygonOffsetUnits = -1;
  });

  // ------------------------------------------------------------------ batching
  var groups = {};
  function group(name) {
    if (!groups[name]) { groups[name] = new THREE.Group(); scene.add(groups[name]); }
    return groups[name];
  }
  var batches = {};
  function addGeo(g, m, geo, mtx) {
    var key = g + "|" + m, b = batches[key] || (batches[key] = { g: g, m: m, p: [], n: [], u: [] });
    var gg = geo.index ? geo.toNonIndexed() : geo.clone();
    if (mtx) gg.applyMatrix4(mtx);
    var p = gg.attributes.position.array, n = gg.attributes.normal.array, uv = gg.attributes.uv;
    for (var i = 0; i < p.length; i++) { b.p.push(p[i]); b.n.push(n[i]); }
    if (uv) for (i = 0; i < uv.array.length; i++) b.u.push(uv.array[i]);
    else for (i = 0; i < p.length / 3 * 2; i++) b.u.push(0);
    gg.dispose();
  }
  var NO_CAST = { glass: 1, water: 1, ao: 1, blob: 1, blobLight: 1, wood: 1, tile: 1, stonefloor: 1,
                  deck: 1, concrete: 1, grass: 1, rugA: 1, rugB: 1, rugC: 1, rugEdge: 1, mirror: 1 };
  function flush() {
    Object.keys(batches).forEach(function (k) {
      var b = batches[k], geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(b.p, 3));
      geo.setAttribute("normal", new THREE.Float32BufferAttribute(b.n, 3));
      geo.setAttribute("uv", new THREE.Float32BufferAttribute(b.u, 2));
      var m = M[b.m], mesh = new THREE.Mesh(geo, m);
      mesh.castShadow = !NO_CAST[b.m];
      mesh.receiveShadow = !m.isMeshBasicMaterial;
      if (m.transparent) mesh.renderOrder = m === M.glass || m === M.water ? 3 : 1;
      group(b.g).add(mesh);
    });
    batches = {};
  }

  // ------------------------------------------------------------------ primitives (plan coords)
  var UNIT = new THREE.BoxGeometry(1, 1, 1);
  function boxUV(sx, sy, sz, metres, ox, oy, oz) {
    // box with texture coordinates in metres (sx along X, sy along Y = height, sz along Z)
    var g = new THREE.BoxGeometry(sx, sy, sz), uv = g.attributes.uv;
    var dims = [[sz, sy, oz, oy], [sz, sy, oz, oy], [sx, sz, ox, oz], [sx, sz, ox, oz], [sx, sy, ox, oy], [sx, sy, ox, oy]];
    for (var f = 0; f < 6; f++) for (var v = 0; v < 4; v++) {
      var i = f * 4 + v, d = dims[f];
      uv.setXY(i, (uv.getX(i) * d[0] + d[2]) / metres, (uv.getY(i) * d[1] + d[3]) / metres);
    }
    return g;
  }
  function pbox(g, m, x0, y0, z0, x1, y1, z1) {
    if (x1 - x0 < 1e-4 || y1 - y0 < 1e-4 || z1 - z0 < 1e-4) return;
    var c = P((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
    if (M[m] && M[m].userData.metres) {
      var geo = boxUV(x1 - x0, z1 - z0, y1 - y0, M[m].userData.metres, x0, z0, -y1);
      addGeo(g, m, geo, new THREE.Matrix4().setPosition(c));
      geo.dispose();
    } else {
      addGeo(g, m, UNIT, new THREE.Matrix4().compose(c, Q0, V(x1 - x0, z1 - z0, y1 - y0)));
    }
  }
  var RB = {};
  function roundedGeo(sx, sy, sz, r) {
    r = Math.max(0.002, Math.min(r, sx / 2 - 0.002, sy / 2 - 0.002, sz / 2 - 0.002));
    var key = [sx, sy, sz, r].map(function (v) { return v.toFixed(3); }).join(",");
    if (RB[key]) return RB[key];
    var w = sx - 2 * r, d = sy - 2 * r, h = Math.max(sz - 2 * r, 0.001), c = Math.min(w, d) * 0.18;
    var s = new THREE.Shape();
    s.moveTo(-w / 2 + c, -d / 2);
    s.lineTo(w / 2 - c, -d / 2); s.quadraticCurveTo(w / 2, -d / 2, w / 2, -d / 2 + c);
    s.lineTo(w / 2, d / 2 - c); s.quadraticCurveTo(w / 2, d / 2, w / 2 - c, d / 2);
    s.lineTo(-w / 2 + c, d / 2); s.quadraticCurveTo(-w / 2, d / 2, -w / 2, d / 2 - c);
    s.lineTo(-w / 2, -d / 2 + c); s.quadraticCurveTo(-w / 2, -d / 2, -w / 2 + c, -d / 2);
    var geo = new THREE.ExtrudeGeometry(s, { depth: h, bevelEnabled: true, bevelThickness: r, bevelSize: r,
      bevelSegments: 2, curveSegments: 3 });
    geo.translate(0, 0, -h / 2);
    geo.applyMatrix4(new THREE.Matrix4().set(1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1));
    return (RB[key] = geo);
  }
  function prbox(g, m, x0, y0, z0, x1, y1, z1, r) {
    addGeo(g, m, roundedGeo(x1 - x0, y1 - y0, z1 - z0, r),
      new THREE.Matrix4().setPosition(P((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)));
  }
  var CYL = {};
  function cylGeo(seg, top) {
    var k = seg + ":" + top;
    return CYL[k] || (CYL[k] = new THREE.CylinderGeometry(top, 1, 1, seg));
  }
  function pcyl(g, m, x, y, z0, z1, rx, ry, seg, top) {
    addGeo(g, m, cylGeo(seg || 20, top == null ? 1 : top),
      new THREE.Matrix4().compose(P(x, y, (z0 + z1) / 2), Q0, V(rx, z1 - z0, ry)));
  }
  var SPH = new THREE.SphereGeometry(1, 18, 12), ICO = new THREE.IcosahedronGeometry(1, 1);
  function psph(g, m, x, y, z, rx, ry, rz, geo) {
    addGeo(g, m, geo || SPH, new THREE.Matrix4().compose(P(x, y, z), Q0, V(rx, rz, ry)));
  }
  function phcyl(g, m, axis, a0, a1, cb, z, r, seg) {
    var q = new THREE.Quaternion().setFromAxisAngle(axis === "x" ? V(0, 0, 1) : V(1, 0, 0), Math.PI / 2);
    var mid = (a0 + a1) / 2, pos = axis === "x" ? P(mid, cb, z) : P(cb, mid, z);
    addGeo(g, m, cylGeo(seg || 14, 1), new THREE.Matrix4().compose(pos, q, V(r, Math.abs(a1 - a0), r)));
  }
  function quad(g, m, x0, y0, x1, y1, z, uvf) {
    var pts = [[x0, y0], [x1, y0], [x1, y1], [x0, y0], [x1, y1], [x0, y1]], pos = [], nor = [], uv = [];
    pts.forEach(function (p) {
      var v = P(p[0], p[1], z);
      pos.push(v.x, v.y, v.z);
      nor.push(0, 1, 0);
      var t = uvf(p[0], p[1]);
      uv.push(t[0], t[1]);
    });
    var geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute("normal", new THREE.Float32BufferAttribute(nor, 3));
    geo.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
    addGeo(g, m, geo);
  }
  function blob(g, x0, y0, x1, y1, z, pad, light) {
    pad = pad == null ? 0.1 : pad;
    var a = x0 - pad, b = y0 - pad, c = x1 + pad, d = y1 + pad;
    quad(g, light ? "blobLight" : "blob", a, b, c, d, z + 0.006, function (x, y) {
      return [(x - a) / (c - a), (y - b) / (d - b)];
    });
  }

  // item frame: u across the front (left to right seen from the front), v from the back (0) to the
  // front (D), z up from the floor; d is the way the item faces
  function F(r, d, z, g) {
    this.r = r; this.d = d; this.z = z; this.g = g;
    var ns = d === "N" || d === "S";
    this.W = ns ? r[2] - r[0] : r[3] - r[1];
    this.D = ns ? r[3] - r[1] : r[2] - r[0];
    this.swap = !ns;
  }
  F.prototype.xy = function (u, v) {
    var r = this.r;
    if (this.d === "S") return [r[0] + u, r[3] - v];
    if (this.d === "N") return [r[2] - u, r[1] + v];
    if (this.d === "E") return [r[0] + v, r[3] - u];
    return [r[2] - v, r[1] + u];
  };
  F.prototype.uOf = function (x, y) {           // across-position of a plan point
    var r = this.r;
    return this.d === "S" ? x - r[0] : this.d === "N" ? r[2] - x : this.d === "E" ? r[3] - y : y - r[1];
  };
  F.prototype.rect = function (u0, v0, u1, v1) {
    var a = this.xy(u0, v0), b = this.xy(u1, v1);
    return [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])];
  };
  F.prototype.box = function (m, u0, v0, z0, u1, v1, z1) {
    var q = this.rect(u0, v0, u1, v1);
    pbox(this.g, m, q[0], q[1], this.z + z0, q[2], q[3], this.z + z1);
  };
  F.prototype.rbox = function (m, u0, v0, z0, u1, v1, z1, r) {
    var q = this.rect(u0, v0, u1, v1);
    prbox(this.g, m, q[0], q[1], this.z + z0, q[2], q[3], this.z + z1, r);
  };
  F.prototype.cyl = function (m, uc, vc, z0, z1, ru, rv, seg, top) {
    var c = this.xy(uc, vc);
    pcyl(this.g, m, c[0], c[1], this.z + z0, this.z + z1, this.swap ? rv : ru, this.swap ? ru : rv, seg, top);
  };
  F.prototype.sph = function (m, uc, vc, zc, ru, rv, rz, geo) {
    var c = this.xy(uc, vc);
    psph(this.g, m, c[0], c[1], this.z + zc, this.swap ? rv : ru, this.swap ? ru : rv, rz, geo);
  };
  F.prototype.hcyl = function (m, axis, a0, a1, cb, zc, r) {    // axis "u" or "v" in the frame
    var p0 = axis === "u" ? this.xy(a0, cb) : this.xy(cb, a0), p1 = axis === "u" ? this.xy(a1, cb) : this.xy(cb, a1);
    if (Math.abs(p0[0] - p1[0]) > Math.abs(p0[1] - p1[1])) phcyl(this.g, m, "x", Math.min(p0[0], p1[0]), Math.max(p0[0], p1[0]), p0[1], this.z + zc, r);
    else phcyl(this.g, m, "y", Math.min(p0[1], p1[1]), Math.max(p0[1], p1[1]), p0[0], this.z + zc, r);
  };
  F.prototype.blob = function (pad, light) {
    blob(this.g, this.r[0], this.r[1], this.r[2], this.r[3], this.z, pad, light);
  };
  function around(p, w, d) { return [p[0] - w / 2, p[1] - d / 2, p[0] + w / 2, p[1] + d / 2]; }

  // ------------------------------------------------------------------ furniture
  function lampOn(f, u, v, z) {
    f.cyl("black", u, v, z, z + 0.025, 0.07, 0.07, 16);
    f.cyl("chrome", u, v, z, z + 0.32, 0.01, 0.01, 8);
    f.cyl("lamp", u, v, z + 0.24, z + 0.44, 0.13, 0.13, 20, 0.72);
  }
  function plantAt(g, x, y, z, s, h, k) {
    // foliage stays within about 1.8 x the pot radius, so plants near walls do not poke through
    var pot = ["pot1", "pot2", "pot3"][k % 3], ph = Math.min(0.42, s * 1.7), leaves = ["leaf1", "leaf2", "leaf3"];
    pcyl(g, pot, x, y, z, z + ph, s, s, 20, 1.12);
    pcyl(g, "soil", x, y, z + ph - 0.03, z + ph - 0.01, s * 1.04, s * 1.04, 16);
    var tall = h > 1.05, n = tall ? 7 : 6;
    if (tall) pcyl(g, "trunk", x, y, z + ph - 0.05, z + h * 0.62, 0.018, 0.018, 6);
    for (var i = 0; i < n; i++) {
      var a = i * 2.4 + k, rr = s * (0.25 + 0.3 * ((i * 37 + k * 11) % 10) / 10);
      var rs = s * ((tall ? 1.05 : 0.95) + 0.25 * ((i + k) % 3) / 2);
      var zz = tall ? z + h * (0.52 + 0.4 * (i % 4) / 3) : z + ph + (h - ph) * (0.35 + 0.45 * (i % 2));
      psph(g, leaves[(i + k) % 3], x + Math.cos(a) * rr, y + Math.sin(a) * rr, Math.min(zz, z + h - rs * 0.8),
        rs, rs, rs * 0.9, ICO);
    }
    blob(g, x - s, y - s, x + s, y + s, z, 0.06);
  }
  function stoolAt(g, x, y, z, seat, k) {
    pcyl(g, "black", x, y, z, z + 0.015, 0.17, 0.17, 18);
    pcyl(g, "frame", x, y, z, z + seat, 0.02, 0.02, 8);
    pcyl(g, "frame", x, y, z + 0.24, z + 0.255, 0.13, 0.13, 16);
    pcyl(g, k % 2 ? "leather" : "fabricDark", x, y, z + seat, z + seat + 0.06, 0.18, 0.18, 20);
    blob(g, x - 0.17, y - 0.17, x + 0.17, y + 0.17, z, 0.05, true);
  }
  function cushions(f, n, u0, u1, v0, v1, z0, z1, m, r) {
    var w = (u1 - u0) / n;
    for (var i = 0; i < n; i++) f.rbox(m, u0 + i * w + 0.008, v0, z0, u0 + (i + 1) * w - 0.008, v1, z1, r);
  }

  var BUILD = {
    bed: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W, D = f.D, dbl = Wd > 1.2;
      f.box("black", 0.1, 0.12, 0, Wd - 0.1, D - 0.12, 0.08);
      f.rbox("bedbase", 0.0, 0.05, 0.08, Wd, D, 0.34, 0.03);
      f.rbox("headboard", -0.04, 0.0, 0.08, Wd + 0.04, 0.09, 1.08, 0.035);
      f.rbox("linen", 0.04, 0.1, 0.32, Wd - 0.04, D - 0.03, 0.56, 0.05);
      var duvet = Wd < 1.5 ? "duvetB" : "duvetA";
      f.rbox(duvet, -0.025, 0.66, 0.42, Wd + 0.025, D + 0.025, 0.6, 0.05);
      f.rbox("linen", -0.02, 0.6, 0.5, Wd + 0.02, 0.86, 0.63, 0.05);
      f.rbox("throw", -0.035, D - 0.6, 0.55, Wd + 0.035, D - 0.2, 0.64, 0.03);
      var n = dbl ? 2 : 1, pw = (Wd - 0.2) / n;
      for (var i = 0; i < n; i++) f.rbox("linen", 0.1 + i * pw + 0.03, 0.13, 0.55, 0.1 + (i + 1) * pw - 0.03, 0.5, 0.72, 0.07);
      f.rbox(dbl ? "cushionA" : "cushionB", Wd / 2 - 0.22, 0.42, 0.57, Wd / 2 + 0.22, 0.56, 0.8, 0.05);
      f.blob(0.12);
    },
    nightstand: function (it, g) {
      var f = new F(it.r, it.d, it.z, g);
      f.rbox("walnut", 0.0, 0.0, 0.12, f.W, f.D, 0.52, 0.015);
      f.box("frame", 0.04, 0.04, 0, 0.06, 0.06, 0.12);
      f.box("frame", f.W - 0.06, 0.04, 0, f.W - 0.04, 0.06, 0.12);
      f.box("frame", 0.04, f.D - 0.06, 0, 0.06, f.D - 0.04, 0.12);
      f.box("frame", f.W - 0.06, f.D - 0.06, 0, f.W - 0.04, f.D - 0.04, 0.12);
      lampOn(f, f.W / 2, f.D * 0.45, 0.52);
      f.blob(0.06, true);
    },
    wardrobe: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), n = Math.max(2, Math.round(f.W / 0.55));
      f.box("black", 0.03, 0.0, 0, f.W - 0.03, f.D - 0.06, 0.08);
      f.box("cabinet", 0, 0, 0.08, f.W, f.D, 2.2);
      for (var i = 1; i < n; i++) f.box("seamline", i * f.W / n - 0.004, f.D, 0.1, i * f.W / n + 0.004, f.D + 0.004, 2.18);
      for (i = 0; i < n; i++) {
        var u = (i + (i % 2 ? 0.12 : 0.88)) * f.W / n;
        f.box("steel", u - 0.008, f.D, 0.9, u + 0.008, f.D + 0.02, 1.3);
      }
      f.blob(0.08);
    },
    hanging: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W, D = f.D;
      f.box("lightwood", 0, 0, 0, 0.025, D, 2.1);
      f.box("lightwood", Wd - 0.025, 0, 0, Wd, D, 2.1);
      f.box("lightwood", 0.025, 0, 1.78, Wd - 0.025, D, 1.81);
      f.box("lightwood", 0.025, 0, 0.0, Wd - 0.025, D, 0.12);
      f.hcyl("chrome", "u", 0.03, Wd - 0.03, D * 0.5, 1.68, 0.012);
      var u = 0.07, k = 0, cl = ["clothA", "clothB", "clothC", "clothD", "clothE", "clothF"];
      while (u < Wd - 0.08) {
        var t = 0.04 + (k % 3) * 0.015, len = [0.75, 0.55, 0.95, 0.62][k % 4];
        f.rbox(cl[(k * 5) % 6], u, D * 0.1, 1.66 - len, u + t, D * 0.9, 1.66, 0.012);
        u += t + 0.025; k++;
      }
      for (var b = 0; b < 3; b++) f.rbox(b % 2 ? "binA" : "binB", 0.08 + b * (Wd - 0.16) / 3, D * 0.15, 1.81, 0.04 + (b + 1) * (Wd - 0.16) / 3, D * 0.85, 2.02, 0.01);
      for (b = 0; b < 4; b++) f.rbox(cl[(b * 3) % 6], 0.1 + b * 0.22, D * 0.3, 0.12, 0.26 + b * 0.22, D * 0.75, 0.2, 0.02);
    },
    shoe: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), h = it.h || 1.0;
      f.box("cabinet", 0, 0, Math.min(0.15, h * 0.2), f.W, f.D, h);
      f.box("oak", -0.01, 0, h, f.W + 0.01, f.D + 0.01, h + 0.03);
      f.box("seamline", f.W / 2 - 0.004, f.D, 0.16, f.W / 2 + 0.004, f.D + 0.004, h - 0.01);
      if (h > 0.9) {
        f.cyl("pot2", f.W * 0.75, f.D * 0.5, h + 0.03, h + 0.12, 0.07, 0.07, 14);
        f.sph("leaf2", f.W * 0.75, f.D * 0.5, h + 0.2, 0.09, 0.09, 0.08, ICO);
      }
      f.blob(0.05, true);
    },
    kitchen: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W, D = f.D;
      f.box("black", 0, 0, 0, Wd, D - 0.07, 0.1);
      f.box("cabinet", 0, 0, 0.1, Wd, D - 0.02, 0.88);
      f.box("worktop", 0, 0, 0.88, Wd, D + 0.01, 0.92);
      for (var u = 0.6; u < Wd - 0.05; u += 0.6) f.box("seamline", u - 0.003, D - 0.02, 0.12, u + 0.003, D - 0.016, 0.86);
      for (u = 0.3; u < Wd; u += 0.6) f.box("steel", u - 0.12, D - 0.02, 0.8, u + 0.12, D + 0.005, 0.815);
      var su = it.sink ? f.uOf(it.sink[0], it.sink[1]) : Wd / 2;
      var hu = su + 0.95 + 0.35 < Wd ? su + 0.95 : su - 0.95;
      f.box("steel", su - 0.38, 0.12, 0.92, su + 0.38, 0.55, 0.922);
      f.box("ceramicIn", su - 0.34, 0.16, 0.9205, su + 0.34, 0.51, 0.9235);
      f.cyl("chrome", su, 0.07, 0.92, 1.2, 0.016, 0.016, 10);
      f.hcyl("chrome", "v", 0.07, 0.3, su, 1.19, 0.013);
      f.box("screen", hu - 0.3, 0.06, 0.92, hu + 0.3, 0.58, 0.926);
      [[-0.14, 0.18], [0.14, 0.18], [-0.14, 0.45], [0.14, 0.45]].forEach(function (b) {
        f.cyl("frame", hu + b[0], b[1], 0.926, 0.928, 0.085, 0.085, 20);
      });
      f.box("screen", hu - 0.29, D - 0.024, 0.14, hu + 0.29, D - 0.012, 0.72);
      var bu = hu > su ? su - 0.85 : su + 0.85;
      f.rbox("oak", bu - 0.2, 0.15, 0.92, bu + 0.2, 0.42, 0.945, 0.008);
      f.cyl("pot1", bu + 0.36, 0.25, 0.92, 1.02, 0.065, 0.065, 14);
      f.sph("leaf1", bu + 0.36, 0.25, 1.09, 0.08, 0.08, 0.07, ICO);
      f.blob(0.06);
    },
    fridge: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W, D = f.D;
      f.box("black", 0.02, 0.0, 0, Wd - 0.02, D - 0.06, 0.06);
      f.rbox("steel", 0.01, 0.0, 0.06, Wd - 0.01, D, 1.92, 0.02);
      f.box("black", 0.03, D - 0.002, 1.13, Wd - 0.03, D + 0.004, 1.145);
      f.box("chrome", 0.06, D, 1.2, 0.085, D + 0.035, 1.8);
      f.box("chrome", 0.06, D, 0.75, 0.085, D + 0.035, 1.05);
      f.box("cabinet", 0, 0, 1.95, Wd, D, 2.25);
      f.box("seamline", 0.02, D, 2.0, Wd - 0.02, D + 0.003, 2.008);
      f.blob(0.06);
    },
    island: function (it, g) {
      var r = it.r, z = it.z, over = Math.min(0.22, (r[3] - r[1]) * 0.28);
      pbox(g, "black", r[0] + 0.06, r[1] + over + 0.04, z, r[2] - 0.06, r[3] - over - 0.04, z + 0.1);
      pbox(g, "cabinet", r[0] + 0.03, r[1] + over, z + 0.1, r[2] - 0.03, r[3] - over, z + 0.88);
      pbox(g, "quartz", r[0], r[1], z + 0.88, r[2], r[3], z + 0.92);
      pbox(g, "quartz", r[0], r[1], z, r[0] + 0.04, r[3], z + 0.88);
      pbox(g, "quartz", r[2] - 0.04, r[1], z, r[2], r[3], z + 0.88);
      var cx = (r[0] + r[2]) / 2, cy = (r[1] + r[3]) / 2;
      pcyl(g, "pot1", cx, cy, z + 0.92, z + 1.0, 0.16, 0.16, 24, 1.15);
      psph(g, "pot3", cx - 0.05, cy, z + 1.0, 0.045, 0.045, 0.045);
      psph(g, "leaf2", cx + 0.06, cy + 0.03, z + 1.0, 0.04, 0.04, 0.04);
      psph(g, "bottleA", cx + 0.02, cy - 0.06, z + 1.0, 0.04, 0.04, 0.04);
      blob(g, r[0], r[1], r[2], r[3], z, 0.06);
    },
    stools: function (it, g) {
      var r = it.r, n = it.n, step = (r[2] - r[0]) / n;
      for (var i = 0; i < n; i++) {
        var x = r[0] + (i + 0.5) * step;
        if (it.sides.indexOf("S") >= 0) stoolAt(g, x, r[1] - 0.1, it.z, 0.64, i);
        if (it.sides.indexOf("N") >= 0) stoolAt(g, x, r[3] + 0.1, it.z, 0.64, i + 1);
      }
    },
    barstool: function (it, g) { stoolAt(g, it.p[0], it.p[1], it.z, 0.74, 1); },
    sofa: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W, D = f.D, arm = 0.17, n = Wd > 1.95 ? 3 : 2;
      f.box("black", 0.1, 0.1, 0, Wd - 0.1, D - 0.1, 0.07);
      f.rbox("fabric", 0, 0, 0.07, Wd, D, 0.42, 0.04);
      f.rbox("fabric", 0, 0, 0.4, Wd, 0.22, 0.84, 0.06);
      f.rbox("fabric", 0, 0, 0.4, arm, D, 0.64, 0.06);
      f.rbox("fabric", Wd - arm, 0, 0.4, Wd, D, 0.64, 0.06);
      cushions(f, n, arm, Wd - arm, 0.2, D - 0.02, 0.4, 0.55, "fabric2", 0.05);
      cushions(f, n, arm, Wd - arm, 0.14, 0.38, 0.52, 0.88, "fabric2", 0.07);
      f.rbox("cushionB", arm + 0.04, 0.28, 0.52, arm + 0.46, 0.44, 0.92, 0.06);
      f.rbox("cushionC", Wd - arm - 0.46, 0.28, 0.52, Wd - arm - 0.04, 0.44, 0.92, 0.06);
      f.blob(0.1);
    },
    armchair: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W, D = f.D;
      f.box("frame", 0.08, 0.08, 0, Wd - 0.08, D - 0.08, 0.12);
      f.rbox("leather", 0, 0, 0.12, Wd, D, 0.4, 0.04);
      f.rbox("leather", 0, 0, 0.38, Wd, 0.18, 0.86, 0.06);
      f.rbox("leather", 0, 0, 0.38, 0.12, D, 0.6, 0.05);
      f.rbox("leather", Wd - 0.12, 0, 0.38, Wd, D, 0.6, 0.05);
      f.rbox("fabric2", 0.13, 0.17, 0.38, Wd - 0.13, D - 0.02, 0.5, 0.05);
      f.rbox("cushionA", 0.18, 0.2, 0.5, Wd - 0.18, 0.34, 0.8, 0.05);
      f.blob(0.08);
    },
    coffee: function (it, g) {
      var r = it.r, z = it.z;
      prbox(g, "oak", r[0], r[1], z + 0.36, r[2], r[3], z + 0.41, 0.02);
      [[0.05, 0.05], [1, 0.05], [0.05, 1], [1, 1]].forEach(function (k) {
        var x = r[0] + 0.03 + k[0] * (r[2] - r[0] - 0.09), y = r[1] + 0.03 + k[1] * (r[3] - r[1] - 0.09);
        pbox(g, "frame", x, y, z, x + 0.03, y + 0.03, z + 0.36);
      });
      var cx = (r[0] + r[2]) / 2, cy = (r[1] + r[3]) / 2;
      pbox(g, "bookA", cx - 0.12, cy - 0.16, z + 0.41, cx + 0.1, cy + 0.0, z + 0.44);
      pbox(g, "bookC", cx - 0.1, cy - 0.15, z + 0.44, cx + 0.08, cy - 0.02, z + 0.465);
      pcyl(g, "pot1", cx + 0.02, cy + 0.17, z + 0.41, z + 0.55, 0.05, 0.05, 14, 0.8);
      blob(g, r[0], r[1], r[2], r[3], z, 0.06, true);
    },
    tv: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W, D = f.D;
      f.box("walnut", 0, 0, 0.16, Wd, D, 0.5);
      f.box("seamline", Wd / 3 - 0.003, D, 0.17, Wd / 3 + 0.003, D + 0.003, 0.49);
      f.box("seamline", 2 * Wd / 3 - 0.003, D, 0.17, 2 * Wd / 3 + 0.003, D + 0.003, 0.49);
      var tw = Math.min(1.25, Wd - 0.05);
      f.box("black", Wd / 2 - tw / 2, 0.0, 0.86, Wd / 2 + tw / 2, 0.05, 1.58);
      f.box("screen", Wd / 2 - tw / 2 + 0.012, 0.05, 0.872, Wd / 2 + tw / 2 - 0.012, 0.053, 1.568);
      f.box("black", Wd / 2 - 0.3, 0.06, 0.5, Wd / 2 + 0.3, 0.14, 0.56);
      f.cyl("pot1", Wd * 0.85, D * 0.5, 0.5, 0.64, 0.06, 0.06, 14);
      f.sph("leaf1", Wd * 0.85, D * 0.5, 0.72, 0.09, 0.09, 0.08, ICO);
      f.blob(0.05, true);
    },
    rug: function (it, g) {
      var r = it.r, z = it.z;
      pbox(g, "rugEdge", r[0], r[1], z + 0.003, r[2], r[3], z + 0.013);
      pbox(g, it.c, r[0] + 0.07, r[1] + 0.07, z + 0.004, r[2] - 0.07, r[3] - 0.07, z + 0.0145);
    },
    plant: function (it, g, k) { plantAt(g, it.p[0], it.p[1], it.z, it.s, it.h, k); },
    table_round: function (it, g) {
      var x = it.p[0], y = it.p[1], z = it.z, s = it.s;
      pcyl(g, "frame", x, y, z, z + 0.02, s * 0.6, s * 0.6, 20);
      pcyl(g, "frame", x, y, z, z + 0.7, 0.025, 0.025, 8);
      pcyl(g, "quartz", x, y, z + 0.7, z + 0.73, s, s, 28);
      pcyl(g, "pot2", x, y, z + 0.73, z + 0.8, 0.05, 0.05, 12);
      blob(g, x - s, y - s, x + s, y + s, z, 0.05, true);
    },
    chair: function (it, g) {
      var f = new F(around(it.p, 0.46, 0.46), it.d, it.z, g);
      [[0.04, 0.04], [0.4, 0.04], [0.04, 0.4], [0.4, 0.4]].forEach(function (k) {
        f.box("frame", k[0], k[1], 0, k[0] + 0.025, k[1] + 0.025, 0.44);
      });
      f.rbox("fabricDark", 0.02, 0.02, 0.42, 0.44, 0.44, 0.48, 0.02);
      f.rbox("fabricDark", 0.02, 0.02, 0.46, 0.44, 0.07, 0.86, 0.02);
      f.blob(0.04, true);
    },
    wc: function (it, g) {
      var x = it.p[0], y = it.p[1], d = it.d;
      var r = d === "N" ? [x - 0.225, y, x + 0.225, y + 0.68] : d === "S" ? [x - 0.225, y - 0.68, x + 0.225, y]
        : d === "E" ? [x, y - 0.225, x + 0.68, y + 0.225] : [x - 0.68, y - 0.225, x, y + 0.225];
      var f = new F(r, d, it.z, g);
      f.box("wall", 0.0, 0.0, 0, 0.45, 0.2, 1.1);
      f.box("tileWhite", -0.005, 0.0, 1.1, 0.455, 0.205, 1.12);
      f.box("chrome", 0.15, 0.2, 0.92, 0.3, 0.205, 1.02);
      f.box("ceramic", 0.13, 0.2, 0.24, 0.32, 0.3, 0.4);
      f.cyl("ceramic", 0.225, 0.45, 0.2, 0.4, 0.18, 0.24, 26, 1.05);
      f.cyl("ceramicIn", 0.225, 0.47, 0.4, 0.405, 0.14, 0.19, 26);
      f.cyl("ceramic", 0.225, 0.45, 0.405, 0.43, 0.188, 0.245, 26);
      f.blob(0.04, true);
    },
    squat: function (it, g) {
      var x = it.p[0], y = it.p[1], ns = it.d === "N" || it.d === "S";
      var r = ns ? [x - 0.21, y - 0.3, x + 0.21, y + 0.3] : [x - 0.3, y - 0.21, x + 0.3, y + 0.21];
      var f = new F(r, it.d, it.z, g);
      f.rbox("ceramic", 0, 0, -0.01, 0.42, 0.6, 0.014, 0.01);
      f.cyl("ceramicIn", 0.21, 0.36, 0.0, 0.016, 0.09, 0.15, 24);
      f.cyl("black", 0.21, 0.42, 0.0, 0.017, 0.04, 0.05, 16);
    },
    basin: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W, D = f.D;
      f.box("walnut", 0.01, 0.0, 0.3, Wd - 0.01, D - 0.02, 0.8);
      f.box("ceramic", -0.01, 0.0, 0.8, Wd + 0.01, D + 0.01, 0.86);
      f.cyl("ceramicIn", Wd / 2, D * 0.56, 0.855, 0.862, Wd * 0.32, D * 0.3, 24);
      f.cyl("chrome", Wd / 2, 0.06, 0.86, 1.02, 0.014, 0.014, 10);
      f.hcyl("chrome", "v", 0.06, 0.17, Wd / 2, 1.005, 0.011);
      f.box("mirror", 0.02, 0.0, 1.05, Wd - 0.02, 0.015, 1.85);
      f.box("frame", 0.0, 0.0, 1.03, Wd, 0.012, 1.87);
      f.blob(0.04, true);
    },
    shower: function (it, g) {
      var r = it.r, z = it.z;
      pbox(g, "tileWhite", r[0], r[1], z, r[2], r[3], z + 0.035);
      var cx = (r[0] + r[2]) / 2, cy = (r[1] + r[3]) / 2;
      pbox(g, "steel", cx - 0.06, cy - 0.06, z + 0.035, cx + 0.06, cy + 0.06, z + 0.037);
      (it.open || []).forEach(function (side) {
        var closed = { N: "S", S: "N", E: "W", W: "E" };
        var ns = side === "N" || side === "S";
        var fixedFrom = ns ? (it.open.indexOf("W") >= 0 ? "E" : "W") : (it.open.indexOf("S") >= 0 ? "N" : "S");
        var L = ns ? r[2] - r[0] : r[3] - r[1], part = L * 0.58, t = 0.012;
        if (ns) {
          var y = side === "N" ? r[3] - 0.03 : r[1] + 0.03;
          var xa = fixedFrom === "E" ? r[2] - part : r[0], xb = fixedFrom === "E" ? r[2] : r[0] + part;
          pbox(g, "glass", xa, y - t, z + 0.035, xb, y + t, z + 2.0);
          pbox(g, "chrome", xa, y - 0.012, z + 1.98, xb, y + 0.012, z + 2.0);
        } else {
          var x = side === "E" ? r[2] - 0.03 : r[0] + 0.03;
          var ya = fixedFrom === "N" ? r[3] - part : r[1], yb = fixedFrom === "N" ? r[3] : r[1] + part;
          pbox(g, "glass", x - t, ya, z + 0.035, x + t, yb, z + 2.0);
          pbox(g, "chrome", x - 0.012, ya, z + 1.98, x + 0.012, yb, z + 2.0);
        }
        void closed;
      });
      pcyl(g, "chrome", cx, cy, z + 2.14, z + 2.16, 0.12, 0.12, 24);
      pcyl(g, "chrome", cx, cy, z + 2.16, z + 2.38, 0.012, 0.012, 8);
    },
    jacuzzi: function (it, g) {
      var r = it.r, z = it.z, t = 0.16, h = 0.62;
      pbox(g, "ceramic", r[0], r[1], z, r[2], r[1] + t, z + h);
      pbox(g, "ceramic", r[0], r[3] - t, z, r[2], r[3], z + h);
      pbox(g, "ceramic", r[0], r[1] + t, z, r[0] + t, r[3] - t, z + h);
      pbox(g, "ceramic", r[2] - t, r[1] + t, z, r[2], r[3] - t, z + h);
      pbox(g, "tileWhite", r[0] + t, r[1] + t, z, r[2] - t, r[3] - t, z + 0.1);
      pbox(g, "water", r[0] + t, r[1] + t, z + 0.1, r[2] - t, r[3] - t, z + h - 0.08);
      prbox(g, "fabricDark", r[0] + t + 0.02, (r[1] + r[3]) / 2 - 0.2, z + h - 0.1, r[0] + t + 0.14, (r[1] + r[3]) / 2 + 0.2, z + h + 0.02, 0.04);
      prbox(g, "fabricDark", r[2] - t - 0.14, (r[1] + r[3]) / 2 - 0.2, z + h - 0.1, r[2] - t - 0.02, (r[1] + r[3]) / 2 + 0.2, z + h + 0.02, 0.04);
      blob(g, r[0], r[1], r[2], r[3], z, 0.08);
    },
    plunge: function (it, g) {
      var r = it.r, z = it.z, t = 0.1, h = 1.0;
      pbox(g, "tileWhite", r[0], r[1], z, r[2], r[1] + t, z + h);
      pbox(g, "tileWhite", r[0], r[3] - t, z, r[2], r[3], z + h);
      pbox(g, "tileWhite", r[0], r[1] + t, z, r[0] + t, r[3] - t, z + h);
      pbox(g, "tileWhite", r[2] - t, r[1] + t, z, r[2], r[3] - t, z + h);
      pbox(g, "water", r[0] + t, r[1] + t, z + 0.1, r[2] - t, r[3] - t, z + h - 0.1);
      pbox(g, "quartz", r[0] + 0.15, r[1] - 0.34, z, r[2] - 0.15, r[1], z + 0.32);
      blob(g, r[0], r[1] - 0.3, r[2], r[3], z, 0.08);
    },
    sauna: function (it, g) {
      var r = it.r, z = it.z, t = 0.07, h = 2.05, door = [r[0] + 0.12, r[0] + 0.72];
      pbox(g, "sauna", r[0], r[3] - t, z, r[2], r[3], z + h);
      pbox(g, "sauna", r[0], r[1] + t, z, r[0] + t, r[3] - t, z + h);
      pbox(g, "sauna", r[2] - t, r[1] + t, z, r[2], r[3] - t, z + h);
      pbox(g, "sauna", r[0], r[1], z, door[0], r[1] + t, z + h);
      pbox(g, "sauna", door[1], r[1], z, r[2], r[1] + t, z + h);
      pbox(g, "sauna", door[0], r[1], z + 1.95, door[1], r[1] + t, z + h);
      pbox(g, "glass", door[0], r[1] + 0.02, z, door[1], r[1] + 0.05, z + 1.95);
      pbox(g, "lightwood", r[0] + t, r[1] + t, z, r[2] - t, r[3] - t, z + 0.02);
      pbox(g, "saunaDark", r[0] + t, r[3] - t - 0.55, z + 0.86, r[2] - t, r[3] - t, z + 0.92);
      pbox(g, "saunaDark", r[0] + t, r[3] - t - 0.55, z, r[2] - t, r[3] - t - 0.5, z + 0.86);
      pbox(g, "saunaDark", r[0] + t, r[3] - t - 1.0, z + 0.42, r[2] - t, r[3] - t - 0.55, z + 0.48);
      pbox(g, "saunaDark", r[0] + t, r[3] - t - 1.0, z, r[2] - t, r[3] - t - 0.96, z + 0.42);
      var hx = r[2] - t - 0.22, hy = r[1] + t + 0.2;
      pbox(g, "frame", hx - 0.17, hy - 0.15, z, hx + 0.17, hy + 0.15, z + 0.62);
      for (var i = 0; i < 9; i++) psph(g, "pot2", hx - 0.1 + (i % 3) * 0.1, hy - 0.08 + Math.floor(i / 3) * 0.08, z + 0.66, 0.05, 0.045, 0.04);
      blob(g, r[0], r[1], r[2], r[3], z, 0.08);
    },
    billiards: function (it, g) {
      var r = it.r, z = it.z;
      [[r[0] + 0.12, r[1] + 0.12], [r[2] - 0.27, r[1] + 0.12], [r[0] + 0.12, r[3] - 0.27], [r[2] - 0.27, r[3] - 0.27]].forEach(function (p) {
        prbox(g, "walnut", p[0], p[1], z, p[0] + 0.15, p[1] + 0.15, z + 0.62, 0.02);
      });
      prbox(g, "walnut", r[0] + 0.05, r[1] + 0.05, z + 0.55, r[2] - 0.05, r[3] - 0.05, z + 0.73, 0.02);
      prbox(g, "walnut", r[0], r[1], z + 0.71, r[2], r[3], z + 0.8, 0.025);
      pbox(g, "felt", r[0] + 0.1, r[1] + 0.1, z + 0.8, r[2] - 0.1, r[3] - 0.1, z + 0.805);
      pbox(g, "felt", r[0] + 0.1, r[1] + 0.1, z + 0.8, r[0] + 0.14, r[3] - 0.1, z + 0.83);
      pbox(g, "felt", r[2] - 0.14, r[1] + 0.1, z + 0.8, r[2] - 0.1, r[3] - 0.1, z + 0.83);
      pbox(g, "felt", r[0] + 0.14, r[1] + 0.1, z + 0.8, r[2] - 0.14, r[1] + 0.14, z + 0.83);
      pbox(g, "felt", r[0] + 0.14, r[3] - 0.14, z + 0.8, r[2] - 0.14, r[3] - 0.1, z + 0.83);
      var cx = (r[0] + r[2]) / 2;
      [[r[0] + 0.1, r[1] + 0.1], [cx, r[1] + 0.085], [r[2] - 0.1, r[1] + 0.1], [r[0] + 0.1, r[3] - 0.1],
       [cx, r[3] - 0.085], [r[2] - 0.1, r[3] - 0.1]].forEach(function (p) {
        pcyl(g, "black", p[0], p[1], z + 0.8, z + 0.832, 0.055, 0.055, 16);
      });
      var bx = r[0] + (r[2] - r[0]) * 0.7, by = (r[1] + r[3]) / 2, cols = ["light", "taillight", "bookC", "bookB", "black", "carB"];
      var k = 0;
      for (var row = 0; row < 3; row++) for (var j = 0; j <= row; j++) {
        psph(g, cols[k++ % cols.length], bx + row * 0.05, by + (j - row / 2) * 0.058, z + 0.833, 0.028, 0.028, 0.028);
      }
      psph(g, "ceramic", r[0] + (r[2] - r[0]) * 0.27, by, z + 0.833, 0.028, 0.028, 0.028);
      phcyl(g, "oak", "x", r[0] + 0.35, r[0] + 1.75, r[1] + 0.32, z + 0.82, 0.011);
      blob(g, r[0], r[1], r[2], r[3], z, 0.12);
    },
    bar: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W, D = f.D;
      f.box("black", 0.02, 0.0, 0, Wd - 0.02, D - 0.05, 0.1);
      f.box("walnut", 0, 0, 0.1, Wd, D, 1.0);
      f.box("worktop", -0.02, 0, 1.0, Wd + 0.02, D + 0.03, 1.05);
      f.box("walnut", 0.1, 0.0, 1.45, Wd - 0.1, 0.24, 1.48);
      var bot = ["bottleG", "bottleA", "bottleC"];
      for (var u = 0.2, k = 0; u < Wd - 0.15; u += 0.11, k++) {
        f.cyl(bot[k % 3], u, 0.12, 1.48, 1.48 + 0.22 + (k % 3) * 0.04, 0.032, 0.032, 12);
      }
      for (u = 0.25; u < Wd - 0.2; u += 0.5) f.cyl("bottleC", u, D * 0.6, 1.05, 1.17, 0.035, 0.035, 12, 1.3);
      f.blob(0.06);
    },
    cuerack: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W;
      f.box("walnut", 0.05, 0, 0.55, Wd - 0.05, 0.03, 1.75);
      for (var i = 0; i < 6; i++) {
        var u = 0.15 + i * (Wd - 0.3) / 5;
        f.cyl(i % 2 ? "oak" : "walnut", u, 0.06, 0.6, 1.68, 0.012, 0.012, 8, 0.6);
      }
    },
    shelves: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W, D = f.D, levels = [0.06, 0.62, 1.18, 1.74];
      f.box("steel", 0, 0, 0, 0.03, D, 1.9);
      f.box("steel", Wd - 0.03, 0, 0, Wd, D, 1.9);
      var mats = ["carton", "binA", "binB", "carton"], k = 0;
      levels.forEach(function (z, li) {
        f.box("binB", 0.03, 0, z, Wd - 0.03, D, z + 0.025);
        var u = 0.06;
        while (u < Wd - 0.25) {
          var w = 0.22 + ((k * 7) % 5) * 0.05, h = 0.2 + ((k * 3) % 4) * 0.06;
          if (u + w > Wd - 0.05) break;
          if (li < 3 || k % 2) f.rbox(mats[k % 4], u, 0.04, z + 0.025, u + w, D - 0.04, z + 0.025 + h, 0.01);
          u += w + 0.04; k++;
        }
      });
    },
    laundry: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W, D = f.D;
      [0, 0.86].forEach(function (z0, i) {
        f.rbox("appliance", 0.02, 0.0, z0, Wd - 0.02, D - 0.02, z0 + 0.84, 0.02);
        f.hcyl("frame", "v", D - 0.03, D, Wd / 2, z0 + 0.42, 0.19);
        f.hcyl(i ? "steel" : "screen", "v", D - 0.025, D + 0.005, Wd / 2, z0 + 0.42, 0.15);
        f.box("black", 0.06, D - 0.021, z0 + 0.74, 0.3, D - 0.015, z0 + 0.8);
      });
      f.box("lightwood", 0.0, 0.0, 1.95, Wd, D, 1.98);
      f.rbox("binA", 0.06, 0.08, 1.98, 0.3, D - 0.12, 2.2, 0.01);
      f.rbox("carton", 0.36, 0.1, 1.98, Wd - 0.06, D - 0.14, 2.15, 0.01);
      f.blob(0.05);
    },
    boiler: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W, D = f.D;
      f.rbox("appliance", 0.0, 0.0, 1.2, Wd, D, 1.95, 0.02);
      f.box("screen", Wd / 2 - 0.08, D, 1.4, Wd / 2 + 0.08, D + 0.004, 1.47);
      for (var i = 0; i < 4; i++) f.cyl(i % 2 ? "copper" : "steel", 0.08 + i * (Wd - 0.16) / 3, D * 0.4, 0.0, 1.2, 0.012, 0.012, 8);
    },
    desk: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W, D = f.D;
      f.rbox("oak", 0, 0, 0.72, Wd, D, 0.75, 0.01);
      f.box("frame", 0.03, 0.03, 0, 0.06, D - 0.03, 0.72);
      f.box("frame", Wd - 0.06, 0.03, 0, Wd - 0.03, D - 0.03, 0.72);
      f.box("black", Wd / 2 - 0.26, 0.06, 0.75, Wd / 2 + 0.26, 0.09, 1.1);
      f.box("screen", Wd / 2 - 0.25, 0.09, 0.77, Wd / 2 + 0.25, 0.092, 1.08);
      lampOn(f, Math.max(0.15, Wd - 0.18), 0.15, 0.75);
      var o = { N: "S", S: "N", E: "W", W: "E" };
      BUILD.chair({ p: f.xy(Wd / 2, D + 0.2), d: o[it.d], z: it.z }, g);
      f.blob(0.06, true);
    },
    dining: function (it, g) {
      var r = it.r, z = it.z;
      prbox(g, "oak", r[0], r[1], z + 0.72, r[2], r[3], z + 0.76, 0.015);
      [[0, 0], [1, 0], [0, 1], [1, 1]].forEach(function (k) {
        var x = r[0] + 0.06 + k[0] * (r[2] - r[0] - 0.17), y = r[1] + 0.06 + k[1] * (r[3] - r[1] - 0.17);
        pbox(g, "frame", x, y, z, x + 0.05, y + 0.05, z + 0.72);
      });
      var cx = (r[0] + r[2]) / 2, cy = (r[1] + r[3]) / 2;
      pcyl(g, "pot1", cx, cy, z + 0.76, z + 0.9, 0.06, 0.06, 14, 0.8);
      psph(g, "leaf1", cx, cy, z + 0.98, 0.09, 0.09, 0.08, ICO);
      (it.chairs || []).forEach(function (c) { BUILD.chair({ p: [c[0], c[1]], d: c[2], z: z }, g); });
      blob(g, r[0], r[1], r[2], r[3], z, 0.12, true);
    },
    bathtub: function (it, g) {
      var r = it.r, z = it.z, t = 0.09, h = 0.56;
      prbox(g, "ceramic", r[0], r[1], z, r[2], r[1] + t, z + h, 0.02);
      prbox(g, "ceramic", r[0], r[3] - t, z, r[2], r[3], z + h, 0.02);
      prbox(g, "ceramic", r[0], r[1] + t, z, r[0] + t, r[3] - t, z + h, 0.02);
      prbox(g, "ceramic", r[2] - t, r[1] + t, z, r[2], r[3] - t, z + h, 0.02);
      pbox(g, "ceramicIn", r[0] + t, r[1] + t, z, r[2] - t, r[3] - t, z + 0.08);
      pbox(g, "water", r[0] + t, r[1] + t, z + 0.08, r[2] - t, r[3] - t, z + h - 0.12);
      var along = (r[2] - r[0]) >= (r[3] - r[1]);
      var fx = along ? r[0] + 0.05 : (r[0] + r[2]) / 2, fy = along ? (r[1] + r[3]) / 2 : r[1] + 0.05;
      pcyl(g, "chrome", fx, fy, z + h, z + h + 0.18, 0.018, 0.018, 10);
      blob(g, r[0], r[1], r[2], r[3], z, 0.06);
    },
    car: function (it, g) {
      var f = new F(it.r, it.d, it.z, g), Wd = f.W, D = f.D, paint = it.c || "carA";
      f.rbox(paint, 0.05, 0.05, 0.28, Wd - 0.05, D - 0.05, 0.86, 0.14);
      f.rbox("carglass", 0.16, D * 0.27, 0.8, Wd - 0.16, D * 0.76, 1.38, 0.14);
      f.rbox(paint, 0.2, D * 0.32, 1.32, Wd - 0.2, D * 0.72, 1.44, 0.06);
      [[0.1, 0.85], [Wd - 0.35, 0.85], [0.1, D - 0.85], [Wd - 0.35, D - 0.85]].forEach(function (w) {
        f.hcyl("tire", "u", w[0], w[0] + 0.25, w[1], 0.33, 0.33);
      });
      f.box("light", 0.2, D - 0.04, 0.62, 0.5, D, 0.72);
      f.box("light", Wd - 0.5, D - 0.04, 0.62, Wd - 0.2, D, 0.72);
      f.box("taillight", 0.2, 0, 0.66, 0.55, 0.04, 0.76);
      f.box("taillight", Wd - 0.55, 0, 0.66, Wd - 0.2, 0.04, 0.76);
      f.blob(0.15);
    },
    tank: function (it, g) {
      var x = it.p[0], y = it.p[1], z = it.z, s = it.s;
      pcyl(g, "appliance", x, y, z + 0.05, z + 1.45, s, s, 24);
      psph(g, "appliance", x, y, z + 1.45, s, s, s * 0.35);
      pcyl(g, "black", x, y, z, z + 0.05, s * 0.8, s * 0.8, 16);
      blob(g, x - s, y - s, x + s, y + s, z, 0.05);
    }
  };

  // ------------------------------------------------------------------ build the house
  S.boxes.forEach(function (b) { pbox(b[7], b[6], b[0], b[1], b[2], b[3], b[4], b[5]); });

  function extrudeYZ(outer, holes, x0, x1) {
    var shape = new THREE.Shape(outer.map(function (p) { return new THREE.Vector2(p[0], p[1]); }));
    holes.forEach(function (h) {
      shape.holes.push(new THREE.Path(h.map(function (p) { return new THREE.Vector2(p[0], p[1]); })));
    });
    var geo = new THREE.ExtrudeGeometry(shape, { depth: x1 - x0, bevelEnabled: false });
    geo.applyMatrix4(new THREE.Matrix4().set(0, 0, 1, x0 - CX, 0, 1, 0, 0, -1, 0, 0, CY, 0, 0, 0, 1));
    return geo;
  }
  function extrudeXZ(outer, holes, y0, y1) {        // outline in (x, z), extruded north from y0 to y1
    var shape = new THREE.Shape(outer.map(function (p) { return new THREE.Vector2(-p[0], p[1]); }));
    holes.forEach(function (h) {
      shape.holes.push(new THREE.Path(h.map(function (p) { return new THREE.Vector2(-p[0], p[1]); })));
    });
    var geo = new THREE.ExtrudeGeometry(shape, { depth: y1 - y0, bevelEnabled: false });
    geo.applyMatrix4(new THREE.Matrix4().set(-1, 0, 0, -CX, 0, 1, 0, 0, 0, 0, -1, CY - y0, 0, 0, 0, 1));
    return geo;
  }
  S.prisms.forEach(function (p) {
    addGeo(p.g, p.m, p.axis === "y" ? extrudeXZ(p.outer, p.holes, p.a0, p.a1) : extrudeYZ(p.outer, p.holes, p.a0, p.a1));
  });

  S.quads.forEach(function (q) {
    var m = FLOOR_MAT[q[5]], k = M[m].userData.metres;
    quad(q[6], m, q[0], q[1], q[2], q[3], q[4], function (x, y) { return [x / k, y / k]; });
  });
  S.ao.forEach(function (a) {
    var x0 = a[0], y0 = a[1], x1 = a[2], y1 = a[3], dir = a[5];
    quad(a[6], "ao", x0, y0, x1, y1, a[4] + 0.004, function (x, y) {
      var t = dir === "N" ? (y - y0) / (y1 - y0) : dir === "S" ? (y1 - y) / (y1 - y0)
        : dir === "E" ? (x - x0) / (x1 - x0) : (x1 - x) / (x1 - x0);
      return [0.5, 1 - t];
    });
  });
  S.items.forEach(function (it, i) {
    var fn = BUILD[it.k];
    if (fn) fn(it, it.f, i);
    else console.warn("no builder for", it.k);
  });

  // gable roof with standing seams (ridge along x or y); flat roofs are boxes in the scene data
  (function () {
    var r = S.roof;
    if (!r || r.type !== "gable") return;
    var ang = Math.atan((r.zR - r.zE) / (r.vM - r.vS)), t = r.t, alongX = r.axis === "x";
    var outline = [[r.vS, r.zE], [r.vM, r.zR], [r.vN, r.zE], [r.vN, r.zE + t], [r.vM, r.zR + t], [r.vS, r.zE + t]];
    addGeo("R", "roof", alongX ? extrudeYZ(outline, [], r.u0, r.u1) : extrudeXZ(outline, [], r.u0, r.u1));
    function plan(u, v) { return alongX ? [u, v] : [v, u]; }       // u along the ridge, v across it
    function zAt(v) { return (v <= r.vM ? r.zE + (v - r.vS) * Math.tan(ang) : r.zE + (r.vN - v) * Math.tan(ang)) + t; }
    function seam(uc, va, vb) {
      var pa = plan(uc, va), pb = plan(uc, vb);
      var a = P(pa[0], pa[1], zAt(va)), b = P(pb[0], pb[1], zAt(vb)), dir = b.clone().sub(a), L = dir.length();
      dir.normalize();
      var q = new THREE.Quaternion().setFromUnitVectors(V(0, 0, 1), dir);
      var c = a.clone().add(b).multiplyScalar(0.5).add(V(0, 0.012, 0));
      addGeo("R", "seam", UNIT, new THREE.Matrix4().compose(c, q, V(0.025, 0.025, L)));
    }
    for (var u = r.u0 + 0.25; u < r.u1 - 0.1; u += 0.5) { seam(u, r.vS, r.vM); seam(u, r.vM, r.vN); }
  })();

  // terrain on a rectilinear grid
  var xs = S.terrain.xs, ys = S.terrain.ys, zz = S.terrain.z;
  (function () {
    var pos = [], uv = [], idx = [];
    for (var j = 0; j < ys.length; j++) for (var i = 0; i < xs.length; i++) {
      var v = P(xs[i], ys[j], zz[j][i]);
      pos.push(v.x, v.y, v.z);
      uv.push(xs[i] / 4, ys[j] / 4);
    }
    var nx = xs.length;
    for (j = 0; j < ys.length - 1; j++) for (i = 0; i < nx - 1; i++) {
      var a = j * nx + i, b = a + 1, c = a + nx, d = c + 1;
      idx.push(a, b, d, a, d, c);
    }
    var geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
    geo.setIndex(idx);
    geo.computeVertexNormals();
    var mesh = new THREE.Mesh(geo, M.grass);
    mesh.receiveShadow = true;
    group("S").add(mesh);
  })();
  function bisect(arr, v) {
    var lo = 0, hi = arr.length - 2;
    while (lo < hi) { var mid = (lo + hi + 1) >> 1; if (arr[mid] <= v) lo = mid; else hi = mid - 1; }
    return lo;
  }
  function groundAt(x, y) {
    var i = bisect(xs, x), j = bisect(ys, y);
    var fx = (x - xs[i]) / (xs[i + 1] - xs[i]), fy = (y - ys[j]) / (ys[j + 1] - ys[j]);
    var z0 = zz[j][i] * (1 - fx) + zz[j][i + 1] * fx, z1 = zz[j + 1][i] * (1 - fx) + zz[j + 1][i + 1] * fx;
    return z0 * (1 - fy) + z1 * fy;
  }
  // boundary wall following the ground, open at the gates
  (function () {
    var plot = S.plot, bound = S.bound;
    if (!plot || !bound || !(bound.h > 0)) return;
    for (var s = 0; s < plot.length; s++) {
      var p0 = plot[s], p1 = plot[(s + 1) % plot.length];
      var len = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]), n = Math.ceil(len / 0.6);
      for (var k = 0; k < n; k++) {
        var t0 = len * k / n, t1 = len * (k + 1) / n;
        var open = (bound.gaps || []).some(function (gp) { return gp[0] === s && t1 > gp[1] && t0 < gp[2]; });
        if (open) continue;
        var mx = p0[0] + (p1[0] - p0[0]) * (k + 0.5) / n, my = p0[1] + (p1[1] - p0[1]) * (k + 0.5) / n;
        var gz = groundAt(mx, my), seg = new THREE.Mesh(UNIT, M.bound);
        seg.scale.set(len / n + 0.02, bound.h + 0.1, 0.2);
        seg.position.copy(P(mx, my, gz + bound.h / 2 - 0.05));
        seg.rotation.y = Math.atan2(p1[1] - p0[1], p1[0] - p0[0]);
        seg.updateMatrix();
        addGeo("S", "bound", UNIT, seg.matrix);
      }
    }
  })();
  // trees, cars and the patio dining set
  S.trees.forEach(function (t, i) {
    var x = t[0], y = t[1], s = t[2], g = groundAt(x, y);
    pcyl("S", "trunk", x, y, g, g + 2.4 * s, 0.13 * s, 0.13 * s, 8, 0.7);
    for (var k = 0; k < 4; k++) {
      var a = k * 1.7 + i, rr = 0.55 * s;
      psph("S", ["leaf1", "leaf2", "leaf3"][(k + i) % 3], x + Math.cos(a) * rr * (k ? 1 : 0), y + Math.sin(a) * rr * (k ? 1 : 0),
        g + (2.9 + (k ? 0.1 * k : 0.7)) * s, 1.25 * s * (k ? 0.85 : 1), 1.25 * s * (k ? 0.85 : 1), 1.1 * s, ICO);
    }
  });
  S.conifers.forEach(function (t) {
    var x = t[0], y = t[1], s = t[2], g = groundAt(x, y);
    pcyl("S", "trunk", x, y, g, g + 1.0 * s, 0.14 * s, 0.14 * s, 8);
    for (var k = 0; k < 3; k++) {
      pcyl("S", "conifer", x, y, g + (0.8 + k * 1.35) * s, g + (3.0 + k * 1.35) * s, (1.5 - k * 0.38) * s, (1.5 - k * 0.38) * s, 9, 0);
    }
  });
  S.cars.forEach(function (c) { BUILD.car({ r: c.r, d: c.d, c: c.c, z: 0.015 }, "S"); });
  if (S.patio) (function () {
    var x = S.patio[0], y = S.patio[1], z = 0.02;
    prbox("S", "oak", x - 0.8, y - 0.45, z + 0.71, x + 0.8, y + 0.45, z + 0.75, 0.02);
    [[-0.72, -0.37], [0.68, -0.37], [-0.72, 0.33], [0.68, 0.33]].forEach(function (k) {
      pbox("S", "frame", x + k[0], y + k[1], z, x + k[0] + 0.04, y + k[1] + 0.04, z + 0.71);
    });
    [[-0.4, -0.72, "N"], [0.4, -0.72, "N"], [-0.4, 0.72, "S"], [0.4, 0.72, "S"]].forEach(function (k) {
      BUILD.chair({ p: [x + k[0], y + k[1]], d: k[2], z: z }, "S");
    });
    pcyl("S", "frame", x, y, z, z + 2.35, 0.02, 0.02, 8);
    pcyl("S", "umbrella", x, y, z + 2.0, z + 2.45, 1.35, 1.35, 16, 0.02);
    blob("S", x - 0.8, y - 0.45, x + 0.8, y + 0.45, z, 0.25, true);
  })();

  flush();

  // shadow catcher under a single floor, so it floats on a soft shadow
  var catcher = new THREE.Mesh(new THREE.PlaneGeometry(60, 50), new THREE.ShadowMaterial({ opacity: 0.16 }));
  catcher.rotation.x = -Math.PI / 2;
  catcher.receiveShadow = true;
  scene.add(catcher);

  // labels
  var labels = [];
  S.labels.forEach(function (l) {
    var div = document.createElement("div");
    div.className = "lbl";
    div.innerHTML = "<b></b><span></span>";
    div.firstChild.textContent = l.en;
    div.lastChild.textContent = l.alt || "";
    if (!l.alt) div.lastChild.style.display = "none";
    var obj = new THREE.CSS2DObject(div);
    obj.position.copy(P(l.p[0], l.p[1], l.p[2]));
    obj.userData.f = l.f;
    scene.add(obj);
    labels.push(obj);
  });

  // ------------------------------------------------------------------ views
  var HOUSE = S.house, LV = {}, LEVELS = S.levels.map(function (l) { return l.id; });
  function levelText(z) { return Math.abs(z) < 0.005 ? "±0.00" : (z > 0 ? "+" : "-") + Math.abs(z).toFixed(2); }
  var NAMES = { house: ["Whole building", ""] };
  S.levels.forEach(function (l) { LV[l.id] = l.z; NAMES[l.id] = [l.name + "  " + levelText(l.z), l.alt || ""]; });
  (function () {                 // buttons: the whole building, then each level from the top down
    var bar = document.getElementById("bar");
    function add(attr, key, label, alt) {
      var b = document.createElement("button");
      b.setAttribute(attr, key);
      b.appendChild(document.createTextNode(label));
      if (alt) { var s = document.createElement("span"); s.className = "alt"; s.textContent = alt; b.appendChild(s); }
      bar.appendChild(b);
    }
    add("data-mode", "house", "Whole building");
    S.levels.slice().reverse().forEach(function (l) { add("data-mode", l.id, l.name, l.alt); });
    add("data-act", "labels", "Labels");
    add("data-act", "save", "Save picture");
    add("data-act", "reset", "Reset view");
    document.getElementById("title").textContent = S.project.title || "3D model";
    document.getElementById("subtitle").textContent = S.project.alt_title || S.project.subtitle || "";
    document.title = (S.project.title || "3D model") + " - 3D";
  })();
  function dirFrom(az, el) {
    var a = az * Math.PI / 180, e = el * Math.PI / 180;
    return V(Math.sin(a) * Math.cos(e), Math.sin(e), -Math.cos(a) * Math.cos(e));
  }
  function corners(b) {
    var out = [];
    [b[0], b[3]].forEach(function (x) { [b[1], b[4]].forEach(function (y) { [b[2], b[5]].forEach(function (z) { out.push(P(x, y, z)); }); }); });
    return out;
  }
  // keep the model clear of the button bar: shift the picture up and fit it in the space left
  function uiBottom() {
    if (STILL) return 0;
    var bar = document.getElementById("bar").getBoundingClientRect();
    return Math.max(0, H() - bar.top + 8);
  }
  function frameOffset() {
    var b = uiBottom();
    if (b > 0) camera.setViewOffset(W(), H(), 0, b / 2, W(), H());
    else camera.clearViewOffset();
  }
  function fit(target, dir, box, margin) {
    var lo = 2, hi = 250, cs = corners(box), yLo = -1 + 2 * uiBottom() / H() + (1 - margin);
    for (var it = 0; it < 32; it++) {
      var mid = (lo + hi) / 2;
      camera.position.copy(target).addScaledVector(dir, mid);
      camera.lookAt(target);
      camera.updateMatrixWorld();
      var ok = cs.every(function (c) {
        var p = c.clone().project(camera);
        return Math.abs(p.x) <= margin && p.y <= margin && p.y >= yLo && p.z < 1;
      });
      if (ok) hi = mid; else lo = mid;
    }
    return hi;
  }
  function viewFor(mode, variant) {
    var B = S.bounds;
    if (mode === "house") {
      return { t: [(B[0] + B[3]) / 2, (B[1] + B[4]) / 2, (B[2] + B[5]) / 2 - 0.8],
               az: variant === "rear" ? S.views.rear : S.views.front, el: 17, box: B, m: 0.86 };
    }
    var z = LV[mode];
    var portrait = W() / H() < 0.85, wide = (HOUSE[2] - HOUSE[0]) > (HOUSE[3] - HOUSE[1]);
    var az = S.views.front - 15 + (variant === "rear" ? 180 : 0) + (portrait && wide ? 90 : 0);
    return { t: [(HOUSE[0] + HOUSE[2]) / 2, (HOUSE[1] + HOUSE[3]) / 2, z + 0.5], az: az, el: portrait ? 60 : 57,
             box: [HOUSE[0], HOUSE[1], z - (LEVELS[0] === mode ? 0.3 : 1.25), HOUSE[2], HOUSE[3], z + 2.4], m: 0.9 };
  }

  var mode = "house", variant = "", showLabels = true;
  var SIDES = { N: [0, 1], S: [0, -1], E: [1, 0], W: [-1, 0] };
  function setVisible(name, on) { if (groups[name]) groups[name].visible = on; }
  function cutaway() {
    if (mode === "house") return;
    var dx = camera.position.x - controls.target.x, dz = camera.position.z - controls.target.z;
    var len = Math.hypot(dx, dz) || 1, px = dx / len, py = -dz / len;
    var tilted = controls.getPolarAngle() > 0.18;
    Object.keys(SIDES).forEach(function (sd) {
      var low = tilted && px * SIDES[sd][0] + py * SIDES[sd][1] > 0.22;
      setVisible(mode + ".lo" + sd, low);
      setVisible(mode + ".hi" + sd, !low);
    });
  }

  // in the whole-house view, garden labels hide when the house stands between them and the camera
  var ray = new THREE.Raycaster(), occluders = [];
  function hideCovered() {
    if (mode !== "house" || !showLabels) return;
    if (!occluders.length) Object.keys(groups).forEach(function (k) {
      if (k === "R" || /\.full$/.test(k)) groups[k].children.forEach(function (m) {
        if (!m.material.transparent) occluders.push(m);
      });
    });
    labels.forEach(function (o) {
      if (o.userData.f !== "S") return;
      var d = o.position.clone().sub(camera.position), len = d.length();
      ray.set(camera.position, d.normalize());
      ray.far = len - 0.3;
      o.visible = ray.intersectObjects(occluders, false).length === 0;
    });
  }
  var needle = document.getElementById("needle");
  function render() {
    cutaway();
    hideCovered();
    renderer.render(scene, camera);
    labelRenderer.render(scene, camera);
    needle.setAttribute("transform", "rotate(" + (controls.getAzimuthalAngle() * 180 / Math.PI) + ")");
  }
  var queued = false;
  function requestRender() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () { queued = false; render(); });
  }
  controls.addEventListener("change", requestRender);

  function placeSun(target, span) {
    var d = dirFrom(222, 52);
    sun.position.copy(target).addScaledVector(d, 40);
    sun.target.position.copy(target);
    var c = sun.shadow.camera;
    c.left = -span; c.right = span; c.top = span; c.bottom = -span; c.near = 5; c.far = 90;
    c.updateProjectionMatrix();
  }

  var userMoved = false;
  controls.addEventListener("start", function () { userMoved = true; });
  function resetView() {
    userMoved = false;
    frameOffset();
    var v = viewFor(mode, variant), target = P(v.t[0], v.t[1], v.t[2]), dir = dirFrom(v.az, v.el);
    var dist = fit(target, dir, v.box, v.m);
    camera.position.copy(target).addScaledVector(dir, dist);
    controls.target.copy(target);
    controls.update();
    render();
  }

  function setMode(m, v) {
    mode = NAMES[m] ? m : "house";
    variant = v || "";
    var house = mode === "house";
    Object.keys(groups).forEach(function (k) {
      var tag = k.split(".")[0], kind = k.split(".")[1] || "";
      var on;
      if (house) on = tag === "R" || tag === "S" || kind === "full" || (kind === "" && LEVELS.indexOf(tag) >= 0);
      else on = tag === mode && (kind === "" || kind === "cut" || kind.indexOf("hi") === 0 || kind.indexOf("lo") === 0);
      groups[k].visible = on;
    });
    catcher.visible = !house;
    if (!house) catcher.position.copy(P(CX, CY, LV[mode] - 0.302));
    scene.background = new THREE.Color(house ? 0xdde7ee : 0xf2f2f0);
    scene.fog = house ? new THREE.Fog(0xdde7ee, 70, 170) : null;
    hemi.intensity = house ? 0.7 : 0.62;
    var span = Math.max(18, Math.hypot(S.bounds[3] - S.bounds[0], S.bounds[4] - S.bounds[1]) * 0.75);
    placeSun(house ? P(CX, CY, 0) : P(CX, CY, LV[mode]), house ? span : 9.5);
    controls.maxPolarAngle = house ? Math.PI * 0.495 : Math.PI * 0.44;
    labels.forEach(function (o) { o.visible = showLabels && (house ? o.userData.f === "S" : o.userData.f === mode); });
    document.getElementById("floorname").textContent = NAMES[mode][0] + (NAMES[mode][1] ? "  ·  " + NAMES[mode][1] : "");
    document.querySelectorAll("#bar button[data-mode]").forEach(function (b) {
      b.classList.toggle("on", b.getAttribute("data-mode") === mode);
    });
    document.querySelector('#bar button[data-act="labels"]').classList.toggle("on", showLabels);
    resetView();
  }

  function savePicture() {
    render();
    var a = document.createElement("a");
    a.href = renderer.domElement.toDataURL("image/png");
    a.download = "model-3d_" + (mode === "house" ? "building" : mode) + ".png";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  document.getElementById("bar").addEventListener("click", function (e) {
    var b = e.target.closest("button");
    if (!b) return;
    if (b.dataset.mode) setMode(b.dataset.mode);
    else if (b.dataset.act === "labels") {
      showLabels = !showLabels;
      labels.forEach(function (o) { o.visible = showLabels && (mode === "house" ? o.userData.f === "S" : o.userData.f === mode); });
      document.querySelector('#bar button[data-act="labels"]').classList.toggle("on", showLabels);
      render();
    } else if (b.dataset.act === "save") savePicture();
    else if (b.dataset.act === "reset") resetView();
  });

  window.addEventListener("resize", function () {
    camera.aspect = W() / H();
    camera.updateProjectionMatrix();
    renderer.setSize(W(), H());
    labelRenderer.setSize(W(), H());
    if (userMoved) { frameOffset(); render(); } else resetView();
  });

  // links: #house, #house-rear, #level-<id>, #level-<id>-rear, plus -nolabels, or -still for clean pictures
  function fromHash() {
    var parts = (location.hash || "").replace("#", "").split("-");
    var key = parts[0] === "level" ? parts[1] : (parts[0] || "house");
    if (!NAMES[key]) key = "house";
    showLabels = parts.indexOf("nolabels") < 0 && parts.indexOf("still") < 0;
    setMode(key, parts.indexOf("rear") >= 0 ? "rear" : "");
  }
  window.addEventListener("hashchange", fromHash);
  fromHash();
  window.APP_READY = true;
  document.title = document.title + " ";
})();
