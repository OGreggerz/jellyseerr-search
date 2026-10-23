//#region node_modules/@lit/reactive-element/css-tag.js
var e = globalThis, t = e.ShadowRoot && (e.ShadyCSS === void 0 || e.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, n = Symbol(), r = /* @__PURE__ */ new WeakMap(), i = class {
	constructor(e, t, r) {
		if (this._$cssResult$ = !0, r !== n) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
		this.cssText = e, this.t = t;
	}
	get styleSheet() {
		let e = this.o, n = this.t;
		if (t && e === void 0) {
			let t = n !== void 0 && n.length === 1;
			t && (e = r.get(n)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), t && r.set(n, e));
		}
		return e;
	}
	toString() {
		return this.cssText;
	}
}, a = (e) => new i(typeof e == "string" ? e : e + "", void 0, n), o = (e, ...t) => new i(e.length === 1 ? e[0] : t.reduce((t, n, r) => t + ((e) => {
	if (!0 === e._$cssResult$) return e.cssText;
	if (typeof e == "number") return e;
	throw Error("Value passed to 'css' function must be a 'css' function result: " + e + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
})(n) + e[r + 1], e[0]), e, n), s = (n, r) => {
	if (t) n.adoptedStyleSheets = r.map((e) => e instanceof CSSStyleSheet ? e : e.styleSheet);
	else for (let t of r) {
		let r = document.createElement("style"), i = e.litNonce;
		i !== void 0 && r.setAttribute("nonce", i), r.textContent = t.cssText, n.appendChild(r);
	}
}, c = t ? (e) => e : (e) => e instanceof CSSStyleSheet ? ((e) => {
	let t = "";
	for (let n of e.cssRules) t += n.cssText;
	return a(t);
})(e) : e, { is: l, defineProperty: u, getOwnPropertyDescriptor: d, getOwnPropertyNames: ee, getOwnPropertySymbols: te, getPrototypeOf: ne } = Object, f = globalThis, re = f.trustedTypes, ie = re ? re.emptyScript : "", ae = f.reactiveElementPolyfillSupport, p = (e, t) => e, m = {
	toAttribute(e, t) {
		switch (t) {
			case Boolean:
				e = e ? ie : null;
				break;
			case Object:
			case Array: e = e == null ? e : JSON.stringify(e);
		}
		return e;
	},
	fromAttribute(e, t) {
		let n = e;
		switch (t) {
			case Boolean:
				n = e !== null;
				break;
			case Number:
				n = e === null ? null : Number(e);
				break;
			case Object:
			case Array: try {
				n = JSON.parse(e);
			} catch {
				n = null;
			}
		}
		return n;
	}
}, oe = (e, t) => !l(e, t), se = {
	attribute: !0,
	type: String,
	converter: m,
	reflect: !1,
	useDefault: !1,
	hasChanged: oe
};
Symbol.metadata ??= Symbol("metadata"), f.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
var h = class extends HTMLElement {
	static addInitializer(e) {
		this._$Ei(), (this.l ??= []).push(e);
	}
	static get observedAttributes() {
		return this.finalize(), this._$Eh && [...this._$Eh.keys()];
	}
	static createProperty(e, t = se) {
		if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
			let n = Symbol(), r = this.getPropertyDescriptor(e, n, t);
			r !== void 0 && u(this.prototype, e, r);
		}
	}
	static getPropertyDescriptor(e, t, n) {
		let { get: r, set: i } = d(this.prototype, e) ?? {
			get() {
				return this[t];
			},
			set(e) {
				this[t] = e;
			}
		};
		return {
			get: r,
			set(t) {
				let a = r?.call(this);
				i?.call(this, t), this.requestUpdate(e, a, n);
			},
			configurable: !0,
			enumerable: !0
		};
	}
	static getPropertyOptions(e) {
		return this.elementProperties.get(e) ?? se;
	}
	static _$Ei() {
		if (this.hasOwnProperty(p("elementProperties"))) return;
		let e = ne(this);
		e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
	}
	static finalize() {
		if (this.hasOwnProperty(p("finalized"))) return;
		if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(p("properties"))) {
			let e = this.properties, t = [...ee(e), ...te(e)];
			for (let n of t) this.createProperty(n, e[n]);
		}
		let e = this[Symbol.metadata];
		if (e !== null) {
			let t = litPropertyMetadata.get(e);
			if (t !== void 0) for (let [e, n] of t) this.elementProperties.set(e, n);
		}
		this._$Eh = /* @__PURE__ */ new Map();
		for (let [e, t] of this.elementProperties) {
			let n = this._$Eu(e, t);
			n !== void 0 && this._$Eh.set(n, e);
		}
		this.elementStyles = this.finalizeStyles(this.styles);
	}
	static finalizeStyles(e) {
		let t = [];
		if (Array.isArray(e)) {
			let n = new Set(e.flat(1 / 0).reverse());
			for (let e of n) t.unshift(c(e));
		} else e !== void 0 && t.push(c(e));
		return t;
	}
	static _$Eu(e, t) {
		let n = t.attribute;
		return !1 === n ? void 0 : typeof n == "string" ? n : typeof e == "string" ? e.toLowerCase() : void 0;
	}
	constructor() {
		super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
	}
	_$Ev() {
		this._$ES = new Promise((e) => this.enableUpdating = e), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((e) => e(this));
	}
	addController(e) {
		(this._$EO ??= /* @__PURE__ */ new Set()).add(e), this.renderRoot !== void 0 && this.isConnected && e.hostConnected?.();
	}
	removeController(e) {
		this._$EO?.delete(e);
	}
	_$E_() {
		let e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
		for (let n of t.keys()) this.hasOwnProperty(n) && (e.set(n, this[n]), delete this[n]);
		e.size > 0 && (this._$Ep = e);
	}
	createRenderRoot() {
		let e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
		return s(e, this.constructor.elementStyles), e;
	}
	connectedCallback() {
		this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(!0), this._$EO?.forEach((e) => e.hostConnected?.());
	}
	enableUpdating(e) {}
	disconnectedCallback() {
		this._$EO?.forEach((e) => e.hostDisconnected?.());
	}
	attributeChangedCallback(e, t, n) {
		this._$AK(e, n);
	}
	_$ET(e, t) {
		let n = this.constructor.elementProperties.get(e), r = this.constructor._$Eu(e, n);
		if (r !== void 0 && !0 === n.reflect) {
			let i = (n.converter?.toAttribute === void 0 ? m : n.converter).toAttribute(t, n.type);
			this._$Em = e, i == null ? this.removeAttribute(r) : this.setAttribute(r, i), this._$Em = null;
		}
	}
	_$AK(e, t) {
		let n = this.constructor, r = n._$Eh.get(e);
		if (r !== void 0 && this._$Em !== r) {
			let e = n.getPropertyOptions(r), i = typeof e.converter == "function" ? { fromAttribute: e.converter } : e.converter?.fromAttribute === void 0 ? m : e.converter;
			this._$Em = r;
			let a = i.fromAttribute(t, e.type);
			this[r] = a ?? this._$Ej?.get(r) ?? a, this._$Em = null;
		}
	}
	requestUpdate(e, t, n, r = !1, i) {
		if (e !== void 0) {
			let a = this.constructor;
			if (!1 === r && (i = this[e]), n ??= a.getPropertyOptions(e), !((n.hasChanged ?? oe)(i, t) || n.useDefault && n.reflect && i === this._$Ej?.get(e) && !this.hasAttribute(a._$Eu(e, n)))) return;
			this.C(e, t, n);
		}
		!1 === this.isUpdatePending && (this._$ES = this._$EP());
	}
	C(e, t, { useDefault: n, reflect: r, wrapped: i }, a) {
		n && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(e) && (this._$Ej.set(e, a ?? t ?? this[e]), !0 !== i || a !== void 0) || (this._$AL.has(e) || (this.hasUpdated || n || (t = void 0), this._$AL.set(e, t)), !0 === r && this._$Em !== e && (this._$Eq ??= /* @__PURE__ */ new Set()).add(e));
	}
	async _$EP() {
		this.isUpdatePending = !0;
		try {
			await this._$ES;
		} catch (e) {
			Promise.reject(e);
		}
		let e = this.scheduleUpdate();
		return e != null && await e, !this.isUpdatePending;
	}
	scheduleUpdate() {
		return this.performUpdate();
	}
	performUpdate() {
		if (!this.isUpdatePending) return;
		if (!this.hasUpdated) {
			if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
				for (let [e, t] of this._$Ep) this[e] = t;
				this._$Ep = void 0;
			}
			let e = this.constructor.elementProperties;
			if (e.size > 0) for (let [t, n] of e) {
				let { wrapped: e } = n, r = this[t];
				!0 !== e || this._$AL.has(t) || r === void 0 || this.C(t, void 0, n, r);
			}
		}
		let e = !1, t = this._$AL;
		try {
			e = this.shouldUpdate(t), e ? (this.willUpdate(t), this._$EO?.forEach((e) => e.hostUpdate?.()), this.update(t)) : this._$EM();
		} catch (t) {
			throw e = !1, this._$EM(), t;
		}
		e && this._$AE(t);
	}
	willUpdate(e) {}
	_$AE(e) {
		this._$EO?.forEach((e) => e.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
	}
	_$EM() {
		this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
	}
	get updateComplete() {
		return this.getUpdateComplete();
	}
	getUpdateComplete() {
		return this._$ES;
	}
	shouldUpdate(e) {
		return !0;
	}
	update(e) {
		this._$Eq &&= this._$Eq.forEach((e) => this._$ET(e, this[e])), this._$EM();
	}
	updated(e) {}
	firstUpdated(e) {}
};
h.elementStyles = [], h.shadowRootOptions = { mode: "open" }, h[p("elementProperties")] = /* @__PURE__ */ new Map(), h[p("finalized")] = /* @__PURE__ */ new Map(), ae?.({ ReactiveElement: h }), (f.reactiveElementVersions ??= []).push("2.1.2");
//#endregion
//#region node_modules/lit-html/lit-html.js
var g = globalThis, ce = (e) => e, _ = g.trustedTypes, le = _ ? _.createPolicy("lit-html", { createHTML: (e) => e }) : void 0, v = "$lit$", y = `lit$${Math.random().toFixed(9).slice(2)}$`, b = "?" + y, ue = `<${b}>`, x = document, S = () => x.createComment(""), C = (e) => e === null || typeof e != "object" && typeof e != "function", w = Array.isArray, T = (e) => w(e) || typeof e?.[Symbol.iterator] == "function", E = "[ 	\n\f\r]", D = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, de = /-->/g, fe = />/g, O = RegExp(`>|${E}(?:([^\\s"'>=/]+)(${E}*=${E}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`, "g"), pe = /'/g, me = /"/g, he = /^(?:script|style|textarea|title)$/i, k = ((e) => (t, ...n) => ({
	_$litType$: e,
	strings: t,
	values: n
}))(1), A = Symbol.for("lit-noChange"), j = Symbol.for("lit-nothing"), ge = /* @__PURE__ */ new WeakMap(), M = x.createTreeWalker(x, 129);
function _e(e, t) {
	if (!w(e) || !e.hasOwnProperty("raw")) throw Error("invalid template strings array");
	return le === void 0 ? t : le.createHTML(t);
}
var ve = (e, t) => {
	let n = e.length - 1, r = [], i, a = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", o = D;
	for (let t = 0; t < n; t++) {
		let n = e[t], s, c, l = -1, u = 0;
		for (; u < n.length && (o.lastIndex = u, c = o.exec(n), c !== null);) u = o.lastIndex, o === D ? c[1] === "!--" ? o = de : c[1] === void 0 ? c[2] === void 0 ? c[3] !== void 0 && (o = O) : (he.test(c[2]) && (i = RegExp("</" + c[2], "g")), o = O) : o = fe : o === O ? c[0] === ">" ? (o = i ?? D, l = -1) : c[1] === void 0 ? l = -2 : (l = o.lastIndex - c[2].length, s = c[1], o = c[3] === void 0 ? O : c[3] === "\"" ? me : pe) : o === me || o === pe ? o = O : o === de || o === fe ? o = D : (o = O, i = void 0);
		let d = o === O && e[t + 1].startsWith("/>") ? " " : "";
		a += o === D ? n + ue : l >= 0 ? (r.push(s), n.slice(0, l) + v + n.slice(l) + y + d) : n + y + (l === -2 ? t : d);
	}
	return [_e(e, a + (e[n] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), r];
}, N = class e {
	constructor({ strings: t, _$litType$: n }, r) {
		let i;
		this.parts = [];
		let a = 0, o = 0, s = t.length - 1, c = this.parts, [l, u] = ve(t, n);
		if (this.el = e.createElement(l, r), M.currentNode = this.el.content, n === 2 || n === 3) {
			let e = this.el.content.firstChild;
			e.replaceWith(...e.childNodes);
		}
		for (; (i = M.nextNode()) !== null && c.length < s;) {
			if (i.nodeType === 1) {
				if (i.hasAttributes()) for (let e of i.getAttributeNames()) if (e.endsWith(v)) {
					let t = u[o++], n = i.getAttribute(e).split(y), r = /([.?@])?(.*)/.exec(t);
					c.push({
						type: 1,
						index: a,
						name: r[2],
						strings: n,
						ctor: r[1] === "." ? ye : r[1] === "?" ? be : r[1] === "@" ? xe : L
					}), i.removeAttribute(e);
				} else e.startsWith(y) && (c.push({
					type: 6,
					index: a
				}), i.removeAttribute(e));
				if (he.test(i.tagName)) {
					let e = i.textContent.split(y), t = e.length - 1;
					if (t > 0) {
						i.textContent = _ ? _.emptyScript : "";
						for (let n = 0; n < t; n++) i.append(e[n], S()), M.nextNode(), c.push({
							type: 2,
							index: ++a
						});
						i.append(e[t], S());
					}
				}
			} else if (i.nodeType === 8) {
				if (i.data === b) c.push({
					type: 2,
					index: a
				});
				else {
					let e = -1;
					for (; (e = i.data.indexOf(y, e + 1)) !== -1;) c.push({
						type: 7,
						index: a
					}), e += y.length - 1;
				}
			}
			a++;
		}
	}
	static createElement(e, t) {
		let n = x.createElement("template");
		return n.innerHTML = e, n;
	}
};
function P(e, t, n = e, r) {
	if (t === A) return t;
	let i = r === void 0 ? n._$Cl : n._$Co?.[r], a = C(t) ? void 0 : t._$litDirective$;
	return i?.constructor !== a && (i?._$AO?.(!1), a === void 0 ? i = void 0 : (i = new a(e), i._$AT(e, n, r)), r === void 0 ? n._$Cl = i : (n._$Co ??= [])[r] = i), i !== void 0 && (t = P(e, i._$AS(e, t.values), i, r)), t;
}
var F = class {
	constructor(e, t) {
		this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
	}
	get parentNode() {
		return this._$AM.parentNode;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	u(e) {
		let { el: { content: t }, parts: n } = this._$AD, r = (e?.creationScope ?? x).importNode(t, !0);
		M.currentNode = r;
		let i = M.nextNode(), a = 0, o = 0, s = n[0];
		for (; s !== void 0;) {
			if (a === s.index) {
				let t;
				s.type === 2 ? t = new I(i, i.nextSibling, this, e) : s.type === 1 ? t = new s.ctor(i, s.name, s.strings, this, e) : s.type === 6 && (t = new Se(i, this, e)), this._$AV.push(t), s = n[++o];
			}
			a !== s?.index && (i = M.nextNode(), a++);
		}
		return M.currentNode = x, r;
	}
	p(e) {
		let t = 0;
		for (let n of this._$AV) n !== void 0 && (n.strings === void 0 ? n._$AI(e[t]) : (n._$AI(e, n, t), t += n.strings.length - 2)), t++;
	}
}, I = class e {
	get _$AU() {
		return this._$AM?._$AU ?? this._$Cv;
	}
	constructor(e, t, n, r) {
		this.type = 2, this._$AH = j, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = n, this.options = r, this._$Cv = r?.isConnected ?? !0;
	}
	get parentNode() {
		let e = this._$AA.parentNode, t = this._$AM;
		return t !== void 0 && e?.nodeType === 11 && (e = t.parentNode), e;
	}
	get startNode() {
		return this._$AA;
	}
	get endNode() {
		return this._$AB;
	}
	_$AI(e, t = this) {
		e = P(this, e, t), C(e) ? e === j || e == null || e === "" ? (this._$AH !== j && this._$AR(), this._$AH = j) : e !== this._$AH && e !== A && this._(e) : e._$litType$ === void 0 ? e.nodeType === void 0 ? T(e) ? this.k(e) : this._(e) : this.T(e) : this.$(e);
	}
	O(e) {
		return this._$AA.parentNode.insertBefore(e, this._$AB);
	}
	T(e) {
		this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
	}
	_(e) {
		this._$AH !== j && C(this._$AH) ? this._$AA.nextSibling.data = e : this.T(x.createTextNode(e)), this._$AH = e;
	}
	$(e) {
		let { values: t, _$litType$: n } = e, r = typeof n == "number" ? this._$AC(e) : (n.el === void 0 && (n.el = N.createElement(_e(n.h, n.h[0]), this.options)), n);
		if (this._$AH?._$AD === r) this._$AH.p(t);
		else {
			let e = new F(r, this), n = e.u(this.options);
			e.p(t), this.T(n), this._$AH = e;
		}
	}
	_$AC(e) {
		let t = ge.get(e.strings);
		return t === void 0 && ge.set(e.strings, t = new N(e)), t;
	}
	k(t) {
		w(this._$AH) || (this._$AH = [], this._$AR());
		let n = this._$AH, r, i = 0;
		for (let a of t) i === n.length ? n.push(r = new e(this.O(S()), this.O(S()), this, this.options)) : r = n[i], r._$AI(a), i++;
		i < n.length && (this._$AR(r && r._$AB.nextSibling, i), n.length = i);
	}
	_$AR(e = this._$AA.nextSibling, t) {
		for (this._$AP?.(!1, !0, t); e !== this._$AB;) {
			let t = ce(e).nextSibling;
			ce(e).remove(), e = t;
		}
	}
	setConnected(e) {
		this._$AM === void 0 && (this._$Cv = e, this._$AP?.(e));
	}
}, L = class {
	get tagName() {
		return this.element.tagName;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	constructor(e, t, n, r, i) {
		this.type = 1, this._$AH = j, this._$AN = void 0, this.element = e, this.name = t, this._$AM = r, this.options = i, n.length > 2 || n[0] !== "" || n[1] !== "" ? (this._$AH = Array(n.length - 1).fill(/* @__PURE__ */ new String()), this.strings = n) : this._$AH = j;
	}
	_$AI(e, t = this, n, r) {
		let i = this.strings, a = !1;
		if (i === void 0) e = P(this, e, t, 0), a = !C(e) || e !== this._$AH && e !== A, a && (this._$AH = e);
		else {
			let r = e, o, s;
			for (e = i[0], o = 0; o < i.length - 1; o++) s = P(this, r[n + o], t, o), s === A && (s = this._$AH[o]), a ||= !C(s) || s !== this._$AH[o], s === j ? e = j : e !== j && (e += (s ?? "") + i[o + 1]), this._$AH[o] = s;
		}
		a && !r && this.j(e);
	}
	j(e) {
		e === j ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
	}
}, ye = class extends L {
	constructor() {
		super(...arguments), this.type = 3;
	}
	j(e) {
		this.element[this.name] = e === j ? void 0 : e;
	}
}, be = class extends L {
	constructor() {
		super(...arguments), this.type = 4;
	}
	j(e) {
		this.element.toggleAttribute(this.name, !!e && e !== j);
	}
}, xe = class extends L {
	constructor(e, t, n, r, i) {
		super(e, t, n, r, i), this.type = 5;
	}
	_$AI(e, t = this) {
		if ((e = P(this, e, t, 0) ?? j) === A) return;
		let n = this._$AH, r = e === j && n !== j || e.capture !== n.capture || e.once !== n.once || e.passive !== n.passive, i = e !== j && (n === j || r);
		r && this.element.removeEventListener(this.name, this, n), i && this.element.addEventListener(this.name, this, e), this._$AH = e;
	}
	handleEvent(e) {
		typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, e) : this._$AH.handleEvent(e);
	}
}, Se = class {
	constructor(e, t, n) {
		this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = n;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	_$AI(e) {
		P(this, e);
	}
}, Ce = {
	M: v,
	P: y,
	A: b,
	C: 1,
	L: ve,
	R: F,
	D: T,
	V: P,
	I,
	H: L,
	N: be,
	U: xe,
	B: ye,
	F: Se
}, we = g.litHtmlPolyfillSupport;
we?.(N, I), (g.litHtmlVersions ??= []).push("3.3.3");
var Te = (e, t, n) => {
	let r = n?.renderBefore ?? t, i = r._$litPart$;
	if (i === void 0) {
		let e = n?.renderBefore ?? null;
		r._$litPart$ = i = new I(t.insertBefore(S(), e), e, void 0, n ?? {});
	}
	return i._$AI(e), i;
}, R = globalThis, z = class extends h {
	constructor() {
		super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
	}
	createRenderRoot() {
		let e = super.createRenderRoot();
		return this.renderOptions.renderBefore ??= e.firstChild, e;
	}
	update(e) {
		let t = this.render();
		this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = Te(t, this.renderRoot, this.renderOptions);
	}
	connectedCallback() {
		super.connectedCallback(), this._$Do?.setConnected(!0);
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this._$Do?.setConnected(!1);
	}
	render() {
		return A;
	}
};
z._$litElement$ = !0, z.finalized = !0, R.litElementHydrateSupport?.({ LitElement: z });
var Ee = R.litElementPolyfillSupport;
Ee?.({ LitElement: z }), (R.litElementVersions ??= []).push("4.2.2");
//#endregion
//#region node_modules/lit-html/directive.js
var B = {
	ATTRIBUTE: 1,
	CHILD: 2,
	PROPERTY: 3,
	BOOLEAN_ATTRIBUTE: 4,
	EVENT: 5,
	ELEMENT: 6
}, De = (e) => (...t) => ({
	_$litDirective$: e,
	values: t
}), Oe = class {
	constructor(e) {}
	get _$AU() {
		return this._$AM._$AU;
	}
	_$AT(e, t, n) {
		this._$Ct = e, this._$AM = t, this._$Ci = n;
	}
	_$AS(e, t) {
		return this.update(e, t);
	}
	update(e, t) {
		return this.render(...t);
	}
}, { I: ke } = Ce, Ae = (e) => e.strings === void 0, je = {}, Me = (e, t = je) => e._$AH = t, Ne = De(class extends Oe {
	constructor(e) {
		if (super(e), e.type !== B.PROPERTY && e.type !== B.ATTRIBUTE && e.type !== B.BOOLEAN_ATTRIBUTE) throw Error("The `live` directive is not allowed on child or event bindings");
		if (!Ae(e)) throw Error("`live` bindings can only contain a single expression");
	}
	render(e) {
		return e;
	}
	update(e, [t]) {
		if (t === A || t === j) return t;
		let n = e.element, r = e.name;
		if (e.type === B.PROPERTY) {
			if (t === n[r]) return A;
		} else if (e.type === B.BOOLEAN_ATTRIBUTE) {
			if (!!t === n.hasAttribute(r)) return A;
		} else if (e.type === B.ATTRIBUTE && n.getAttribute(r) === t + "") return A;
		return Me(e), t;
	}
});
//#endregion
//#region src/ha.ts
function Pe(e, t, n) {
	e.dispatchEvent(new CustomEvent(t, {
		detail: n,
		bubbles: !0,
		composed: !0
	}));
}
function V(e, t) {
	Pe(e, "hass-notification", { message: t });
}
function H(e) {
	return e && typeof e == "object" && "message" in e ? String(e.message) : String(e);
}
//#endregion
//#region src/logic.ts
var Fe = /* @__PURE__ */ new Set([
	"not_requested",
	"unknown",
	"deleted"
]);
function U(e) {
	return Fe.has(e);
}
function W(e) {
	switch (e) {
		case "pending": return "Requested";
		case "processing": return "Processing";
		case "partially_available": return "Partial";
		case "available": return "Available";
		case "blacklisted": return "Blocked";
		default: return null;
	}
}
function Ie(e) {
	return e === "available" || e === "partially_available" || e === "processing";
}
function G(e) {
	return e.filter((e) => U(e.status)).map((e) => e.season_number);
}
function Le(e) {
	return U(e) || e === "partially_available";
}
function Re(e) {
	return e.status === "missing" || e.status === "not_aired" && !e.monitored;
}
function ze(e) {
	return e.filter(Re).map((e) => e.id);
}
function Be(e) {
	switch (e.status) {
		case "downloaded": return "Downloaded";
		case "downloading": return "Downloading";
		case "wanted": return "Not found yet";
		case "not_aired": return e.monitored ? "When it airs" : "Not aired";
		default: return null;
	}
}
function Ve(e) {
	if (!e) return "No air date";
	let [t, n, r] = e.split("-").map(Number), i = [
		"Jan",
		"Feb",
		"Mar",
		"Apr",
		"May",
		"Jun",
		"Jul",
		"Aug",
		"Sep",
		"Oct",
		"Nov",
		"Dec"
	][n - 1];
	return i ? `${r} ${i} ${t}` : e;
}
var He = [
	"Jan",
	"Feb",
	"Mar",
	"Apr",
	"May",
	"Jun",
	"Jul",
	"Aug",
	"Sep",
	"Oct",
	"Nov",
	"Dec"
];
function K(e) {
	let [t, n, r] = e.slice(0, 10).split("-").map(Number);
	return `${r} ${He[n - 1]} ${t}`;
}
function Ue(e, t = /* @__PURE__ */ new Date()) {
	let n = new Date(e), r = n.toLocaleTimeString("en-GB", {
		hour: "2-digit",
		minute: "2-digit"
	}), i = (e) => new Date(e.getFullYear(), e.getMonth(), e.getDate()).getTime(), a = Math.round((i(n) - i(t)) / 864e5);
	return a === 0 ? `today ${r}` : a === 1 ? `tomorrow ${r}` : `${n.toLocaleDateString("en-GB", {
		weekday: "short",
		day: "numeric",
		month: "short"
	})}, ${r}`;
}
function We(e, t = /* @__PURE__ */ new Date()) {
	let n = Math.max(0, Math.round((t.getTime() - new Date(e).getTime()) / 6e4));
	if (n < 60) return n <= 1 ? "just now" : `${n} minutes ago`;
	let r = Math.round(n / 60);
	return r < 48 ? `${r} hour${r === 1 ? "" : "s"} ago` : `${Math.round(r / 24)} days ago`;
}
function Ge(e) {
	return {
		downloading: "Downloading",
		not_found: "Not found yet",
		not_out: "Not out yet"
	}[e.state];
}
function Ke(e, t = /* @__PURE__ */ new Date()) {
	if (e.state === "downloading") return "Downloading now.";
	if (e.media_type === "tv") {
		let n = [];
		e.missing && n.push(`${e.missing} episode${e.missing === 1 ? "" : "s"} out but not found yet`);
		let r = e.next_episode;
		return r && n.push(`Next: S${r.season}E${r.episode} ${Ue(r.air_date_utc, t)}`), e.state === "not_found" && e.last_search && n.push(`last searched ${We(e.last_search, t)}`), n.length ? n.join(" · ") : "No upcoming episodes listed yet.";
	}
	if (e.state === "not_found") {
		let n = e.digital_release ?? e.physical_release, r = n ? `Out since ${K(n)}` : "Out";
		return e.last_search ? `${r} · last searched ${We(e.last_search, t)}` : r;
	}
	return e.expected_basis === "digital" ? `Digital release ${K(e.expected)}` : e.expected_basis === "physical" ? `Blu-ray/DVD release ${K(e.expected)}` : e.expected_basis === "cinema_plus_90" && e.in_cinemas ? `${`In cinemas from ${K(e.in_cinemas)}`} · no home release date yet (counted as out around ${K(e.expected)})` : e.release_status === "announced" ? "Announced · no release date yet" : "No release date yet";
}
function qe(e) {
	let t = e.episode ? ` for S${e.episode.season}E${e.episode.episode}` : "";
	if (!e.found) return `Nothing posted yet${t}.`;
	if (e.accepted) return `${e.accepted} suitable cop${e.accepted === 1 ? "y" : "ies"} found${t}${e.best ? `: ${e.best}` : ""}.`;
	let n = e.reasons.length ? ` (${e.reasons[0]})` : "";
	return `${e.found} cop${e.found === 1 ? "y" : "ies"} found${t}, none your profile accepts${n}.`;
}
function Je(e, t, n) {
	if (t === "tv") return e.next_air_date ? `Next episode ${K(e.next_air_date)}` : e.tmdb_status === "Ended" || e.tmdb_status === "Canceled" ? `Ended${e.last_air_date ? ` · last aired ${K(e.last_air_date)}` : ""}` : e.last_air_date ? `No next episode announced · last aired ${K(e.last_air_date)}` : null;
	let r = [e.digital, e.physical].filter((e) => !!e).sort()[0];
	return r && r <= n ? `Out to buy or stream since ${K(r)}` : e.digital && e.digital > n ? `Digital release ${K(e.digital)}` : e.physical && e.physical > n ? `Blu-ray/DVD release ${K(e.physical)}` : e.theatrical && e.theatrical <= n ? `In cinemas from ${K(e.theatrical)} · no digital release date yet` : e.theatrical ? `In cinemas ${K(e.theatrical)}` : e.tmdb_status && e.tmdb_status !== "Released" ? `Not released yet (${e.tmdb_status.toLowerCase()})` : null;
}
function q(e, t) {
	let n = t.trim().toLowerCase();
	return n ? e.filter((e) => e.title.toLowerCase().includes(n)) : [...e];
}
var J = class {
	constructor() {
		this._seq = 0;
	}
	next() {
		let e = ++this._seq;
		return () => e === this._seq;
	}
}, Y, Ye = "0.10.0", X = "jellyseerr_search", Xe = 400, Z = 2, Ze = 36e5, Qe = [2e4, 6e4], $e = !1, Q = !1, et = [
	{
		value: "all",
		label: "All"
	},
	{
		value: "movie",
		label: "Movies"
	},
	{
		value: "tv",
		label: "TV"
	},
	{
		value: "downloaded",
		label: "Downloaded"
	},
	{
		value: "waiting",
		label: "Waiting"
	}
], tt = [{
	value: "trending",
	label: "Trending",
	heading: "Trending today"
}, {
	value: "popular",
	label: "Popular",
	heading: "Popular"
}];
function nt(e, t) {
	return t === "daily" ? `${e} is released by date, so it's now set up as a daily show.` : `${e} isn't released by date, so it's no longer set up as a daily show.`;
}
var $ = class extends z {
	constructor() {
		super(), this._latestSearch = new J(), this._latestSeasons = new J(), this._latestBrowse = new J(), this._latestEpisodes = new J(), this._latestLibrary = new J(), this._refreshTimers = [], this._browseAt = 0, this._query = "", this._filter = "all", this._browse = "trending", this._loading = !1, this._chosen = /* @__PURE__ */ new Set(), this._is4k = !1, this._requesting = !1, this._confirmRemove = !1, this._removing = !1, this._picker = !1, this._picked = /* @__PURE__ */ new Set(), this._pickerBusy = !1, this._downloading = !1, this._followBusy = !1, this._checks = {}, this._waitingOn = Q;
	}
	static getConfigForm() {
		return {
			schema: [
				{
					name: "title",
					selector: { text: {} }
				},
				{
					name: "media_type",
					selector: { select: {
						mode: "dropdown",
						options: [
							{
								value: "all",
								label: "Movies and TV shows"
							},
							{
								value: "movie",
								label: "Movies"
							},
							{
								value: "tv",
								label: "TV shows"
							}
						]
					} }
				},
				{
					name: "show_trending",
					selector: { boolean: {} }
				},
				{
					name: "show_4k",
					selector: { boolean: {} }
				},
				{
					name: "show_remove",
					selector: { boolean: {} }
				},
				{
					name: "config_entry_id",
					selector: { config_entry: { integration: X } }
				}
			],
			computeLabel: (e) => ({
				title: "Title",
				media_type: "Default filter",
				show_trending: "Show trending and popular titles before searching",
				show_4k: "Offer 4K requests",
				show_remove: "Offer Remove (deletes the files from Radarr/Sonarr)",
				config_entry_id: "Jellyseerr server (only if you have several)"
			})[e.name]
		};
	}
	static getStubConfig() {
		return { title: "Request movies & TV" };
	}
	setConfig(e) {
		if (!e) throw Error("Invalid configuration");
		if (e.media_type && !et.some((t) => t.value === e.media_type)) throw Error("media_type must be all, movie or tv");
		this._config = e, this._filter = e.media_type ?? "all";
	}
	getCardSize() {
		return this._results?.length || this._showBrowse() && this._browseResults?.length ? 8 : 2;
	}
	getGridOptions() {
		return {
			columns: 12,
			min_columns: 6,
			rows: "auto"
		};
	}
	disconnectedCallback() {
		super.disconnectedCallback(), clearTimeout(this._debounce), this._clearRefreshTimers();
	}
	updated(e) {
		e.has("hass") && this.hass && !$e && ($e = !0, this._checkVersion()), e.has("hass") && this.hass && this._browseDue() && this._loadBrowse();
	}
	async _checkVersion() {
		try {
			let { version: e, waiting: t } = await this.hass.callWS({ type: `${X}/version` });
			e !== "0.10.0" && (this._staleVersion = e), Q = !!t, this._waitingOn = Q;
		} catch {}
	}
	async _reload() {
		try {
			if ("caches" in window) for (let e of await caches.keys()) await caches.delete(e);
		} finally {
			location.reload();
		}
	}
	_entry() {
		return this._config.config_entry_id ? { config_entry_id: this._config.config_entry_id } : {};
	}
	async _loadWaiting() {
		this._waitingError = void 0;
		try {
			let { results: e } = await this.hass.callWS({
				type: `${X}/waiting`,
				...this._entry()
			});
			this._filter === "waiting" && (this._waiting = e);
		} catch (e) {
			this._filter === "waiting" && (this._waitingError = H(e));
		}
	}
	_key(e) {
		return `${e.media_type}/${e.arr_id}`;
	}
	async _checkWaiting(e) {
		let t = this._key(e);
		this._checks = {
			...this._checks,
			[t]: "checking"
		};
		try {
			let n = await this.hass.callWS({
				type: `${X}/waiting/check`,
				media_type: e.media_type,
				arr_id: e.arr_id,
				...this._entry()
			});
			this._checks = {
				...this._checks,
				[t]: n
			};
		} catch (e) {
			this._checks = {
				...this._checks,
				[t]: `Check failed: ${H(e)}`
			};
		}
	}
	async _searchWaiting(e) {
		try {
			await this.hass.callWS({
				type: `${X}/waiting/search`,
				media_type: e.media_type,
				arr_id: e.arr_id,
				...this._entry()
			}), V(this, `Searching for ${e.title} now. It downloads by itself if a suitable copy turns up.`), setTimeout(() => {
				this._filter === "waiting" && !this._selected && this._loadWaiting();
			}, 3e4);
		} catch (e) {
			V(this, `Search failed: ${H(e)}`);
		}
	}
	_openWaiting(e) {
		e.tmdb_id && this._open({
			tmdb_id: e.tmdb_id,
			media_type: e.media_type,
			title: e.title,
			year: e.year,
			overview: "",
			poster_url: e.poster_url,
			status: "processing"
		});
	}
	_showBrowse() {
		return this._filter !== "downloaded" && this._filter !== "waiting" && this._config.show_trending !== !1 && this._query.trim().length < Z;
	}
	async _loadLibrary() {
		let e = this._latestLibrary.next();
		this._libraryError = void 0;
		try {
			let { results: t } = await this.hass.callWS({
				type: `${X}/library`,
				...this._entry()
			});
			e() && (this._library = t);
		} catch (t) {
			e() && (this._libraryError = H(t));
		}
	}
	_browseDue() {
		return !this._showBrowse() || this._selected ? !1 : this._browseKey !== `${this._browse}/${this._filter}` || Date.now() - this._browseAt > Ze;
	}
	async _loadBrowse() {
		let e = this._latestBrowse.next(), t = `${this._browse}/${this._filter}`;
		this._browseKey !== t && (this._browseResults = void 0), this._browseKey = t, this._browseAt = Date.now(), this._browseError = void 0;
		try {
			let { results: t } = await this.hass.callWS({
				type: `${X}/${this._browse}`,
				media_type: this._filter,
				...this._entry()
			});
			e() && (this._browseResults = t);
		} catch (t) {
			e() && (this._browseError = H(t));
		}
	}
	_setBrowse(e) {
		e !== this._browse && (this._browse = e, this._browseDue() && this._loadBrowse());
	}
	_onInput(e) {
		this._query = e.target.value, clearTimeout(this._debounce), this._filter !== "downloaded" && this._filter !== "waiting" && (this._debounce = setTimeout(() => void this._search(), Xe));
	}
	_onKeydown(e) {
		e.key === "Enter" && (clearTimeout(this._debounce), e.target.blur(), this._search());
	}
	_clear() {
		this._leaveShow(), clearTimeout(this._debounce), this._latestSearch.next(), this._query = "", this._results = void 0, this._error = void 0, this._loading = !1, this._selected = void 0;
	}
	_setFilter(e) {
		e !== this._filter && (this._filter = e, e === "downloaded" ? this._loadLibrary() : e === "waiting" ? this._loadWaiting() : this._query.trim().length >= Z ? this._search() : this._browseDue() && this._loadBrowse());
	}
	async _search() {
		if (this._filter === "downloaded" || this._filter === "waiting") return;
		let e = this._query.trim();
		if (e.length < Z) {
			this._latestSearch.next(), this._results = void 0, this._loading = !1;
			return;
		}
		let t = this._latestSearch.next();
		this._loading = !0, this._error = void 0;
		try {
			let { results: n } = await this.hass.callWS({
				type: `${X}/search`,
				query: e,
				media_type: this._filter,
				...this._entry()
			});
			if (!t()) return;
			this._results = n, this._selected = void 0;
		} catch (e) {
			t() && (this._error = H(e));
		} finally {
			t() && (this._loading = !1);
		}
	}
	_open(e) {
		this._leaveShow(), this._selected = e, this._seasons = void 0, this._seasonsError = void 0, this._chosen = /* @__PURE__ */ new Set(), this._is4k = !1, this._confirmRemove = !1, this._picker = !1, this._show = void 0, this._release = void 0, this._closeEpisodes(), this._loadRelease(e), e.media_type === "tv" && this._loadSeasons(e.tmdb_id);
	}
	async _loadRelease(e) {
		try {
			let t = await this.hass.callWS({
				type: `${X}/release`,
				tmdb_id: e.tmdb_id,
				media_type: e.media_type,
				...this._entry()
			});
			this._selected === e && (this._release = t);
		} catch {}
	}
	async _loadSeasons(e) {
		let t = this._latestSeasons.next();
		try {
			let { seasons: n, episode_picker: r, show: i } = await this.hass.callWS({
				type: `${X}/seasons`,
				tmdb_id: e,
				...this._entry()
			});
			if (!t()) return;
			this._seasons = n, this._picker = !!r, this._show = i, this._chosen = new Set(G(n));
		} catch (e) {
			t() && (this._seasonsError = H(e));
		}
	}
	_toggleSeason(e) {
		let t = new Set(this._chosen);
		t.has(e) ? t.delete(e) : t.add(e), this._chosen = t;
	}
	_toggleAllSeasons() {
		let e = G(this._seasons ?? []);
		this._chosen = this._chosen.size === e.length ? /* @__PURE__ */ new Set() : new Set(e);
	}
	async _request() {
		let e = this._selected;
		if (!e || this._requesting) return;
		let t = {
			type: `${X}/request`,
			tmdb_id: e.tmdb_id,
			media_type: e.media_type,
			is_4k: this._is4k,
			...this._entry()
		};
		e.media_type === "tv" && (t.seasons = this._seasons ? [...this._chosen].sort((e, t) => e - t) : "all"), this._requesting = !0;
		try {
			await this.hass.callWS(t), V(this, `Requested ${e.title}`), this._markRequested(e);
		} catch (e) {
			V(this, `Request failed: ${H(e)}`);
		} finally {
			this._requesting = !1;
		}
	}
	async _remove() {
		let e = this._selected;
		if (e && !this._removing) {
			if (!this._confirmRemove) {
				this._confirmRemove = !0;
				return;
			}
			this._removing = !0;
			try {
				await this.hass.callWS({
					type: `${X}/remove`,
					tmdb_id: e.tmdb_id,
					media_type: e.media_type,
					...this._entry()
				}), V(this, `Removed ${e.title}`), this._setStatus(e, "deleted"), this._library = this._library?.filter((t) => t.tmdb_id !== e.tmdb_id || t.media_type !== e.media_type);
			} catch (e) {
				V(this, `Remove failed: ${H(e)}`);
			} finally {
				this._removing = !1, this._confirmRemove = !1;
			}
		}
	}
	_setStatus(e, t) {
		let n = {
			...e,
			status: t
		}, r = (t) => t?.map((t) => t.tmdb_id === e.tmdb_id && t.media_type === e.media_type ? n : t);
		this._results = r(this._results), this._browseResults = r(this._browseResults), this._selected === e && (this._selected = n), this._seasons && t === "deleted" && (this._seasons = this._seasons.map((e) => ({
			...e,
			status: "deleted"
		})));
	}
	_markRequested(e) {
		let t = e.status === "partially_available" ? e.status : "pending", n = {
			...e,
			status: t
		}, r = (t) => t?.map((t) => t.tmdb_id === e.tmdb_id && t.media_type === e.media_type ? n : t);
		this._results = r(this._results), this._browseResults = r(this._browseResults), this._selected === e && (this._selected = n), this._seasons && (this._seasons = this._seasons.map((e) => this._chosen.has(e.season_number) ? {
			...e,
			status: "pending"
		} : e), this._chosen = /* @__PURE__ */ new Set());
	}
	_openEpisodes(e, t) {
		t.preventDefault(), t.stopPropagation(), this._selected && (this._episodeSeason = e, this._episodes = void 0, this._episodesError = void 0, this._picked = /* @__PURE__ */ new Set(), this._loadEpisodes(this._selected.tmdb_id, e.season_number));
	}
	async _loadEpisodes(e, t) {
		let n = this._latestEpisodes.next();
		try {
			let r = await this.hass.callWS({
				type: `${X}/episodes`,
				tmdb_id: e,
				season_number: t,
				...this._entry()
			});
			if (!n()) return;
			r.added && (this._addedSeries = r.series_id), this._episodes = r;
		} catch (e) {
			n() && (this._episodesError = H(e));
		}
	}
	_clearRefreshTimers() {
		this._refreshTimers.forEach(clearTimeout), this._refreshTimers = [];
	}
	_closeEpisodes() {
		this._confirmRemoveEp = void 0, this._clearRefreshTimers(), this._latestEpisodes.next(), this._episodeSeason = void 0, this._episodes = void 0, this._episodesError = void 0, this._picked = /* @__PURE__ */ new Set();
	}
	_leaveShow() {
		let e = this._addedSeries;
		this._addedSeries = void 0, e !== void 0 && this.hass && this.hass.callWS({
			type: `${X}/episodes/discard`,
			series_id: e,
			...this._entry()
		}).catch(() => void 0);
	}
	_back() {
		this._leaveShow(), this._closeEpisodes(), this._selected = void 0, this._filter === "downloaded" && this._loadLibrary(), this._filter === "waiting" && this._loadWaiting();
	}
	_togglePick(e) {
		let t = new Set(this._picked);
		t.has(e) ? t.delete(e) : t.add(e), this._picked = t;
	}
	_toggleAllPicks() {
		let e = ze(this._episodes?.episodes ?? []);
		this._picked = this._picked.size === e.length ? /* @__PURE__ */ new Set() : new Set(e);
	}
	_stillOn(e, t) {
		return this._selected === e && this._episodes?.series_id === t;
	}
	_recoverIfGone(e, t, n) {
		return e?.translation_key === "series_gone" && (V(this, `${t.title} had been tidied out of Sonarr. It's back now: try again.`), this._selected === t && this._loadEpisodes(t.tmdb_id, n), !0);
	}
	async _download() {
		let e = this._episodes, t = this._selected;
		if (!e || !t || !this._picked.size || this._pickerBusy) return;
		let n = [...this._picked];
		this._pickerBusy = !0, this._downloading = !0;
		try {
			let r = await this.hass.callWS({
				type: `${X}/episodes/download`,
				series_id: e.series_id,
				episode_ids: n,
				...this._entry()
			});
			this._addedSeries === e.series_id && (this._addedSeries = void 0);
			let i = r.series_type_changed ? ` ${nt(e.title, r.series_type_changed)}` : "";
			if (V(this, `Downloading ${n.length} episode${n.length === 1 ? "" : "s"} of ${e.title}.${i}`), !this._stillOn(t, e.series_id)) return;
			this._picked = /* @__PURE__ */ new Set(), await this._loadEpisodes(t.tmdb_id, e.season_number), this._clearRefreshTimers(), this._refreshTimers = Qe.map((n) => setTimeout(() => {
				this._stillOn(t, e.series_id) && this._loadEpisodes(t.tmdb_id, e.season_number);
			}, n));
		} catch (n) {
			this._recoverIfGone(n, t, e.season_number) || V(this, `Download failed: ${H(n)}`);
		} finally {
			this._pickerBusy = !1, this._downloading = !1;
		}
	}
	_askRemoveEpisode(e, t) {
		t.preventDefault(), t.stopPropagation(), this._confirmRemoveEp = e;
	}
	async _removeEpisode(e) {
		let t = this._episodes, n = this._selected;
		if (t && n && !this._pickerBusy) {
			this._pickerBusy = !0;
			try {
				let r = await this.hass.callWS({
					type: `${X}/episodes/remove`,
					series_id: t.series_id,
					tmdb_id: n.tmdb_id,
					episode_ids: [e.id],
					...this._entry()
				});
				this._confirmRemoveEp = void 0, r.show_removed ? (V(this, `Removed episode ${e.episode_number}. Nothing else was left, so ${t.title} is gone.`), this._addedSeries === t.series_id && (this._addedSeries = void 0), this._library = this._library?.filter((e) => e.tmdb_id !== n.tmdb_id || e.media_type !== n.media_type), this._setStatus(n, "not_requested"), this._stillOn(n, t.series_id) && (this._closeEpisodes(), this._loadSeasons(n.tmdb_id))) : (V(this, `Removed episode ${e.episode_number} of ${t.title}`), this._stillOn(n, t.series_id) && await this._loadEpisodes(n.tmdb_id, t.season_number));
			} catch (e) {
				this._recoverIfGone(e, n, t.season_number) || V(this, `Remove failed: ${H(e)}`);
			} finally {
				this._pickerBusy = !1;
			}
		}
	}
	async _setFollowShow(e) {
		let t = this._selected;
		if (t && !this._followBusy) {
			this._followBusy = !0;
			try {
				let n = await this.hass.callWS({
					type: `${X}/episodes/follow`,
					tmdb_id: t.tmdb_id,
					follow_new: e,
					...this._entry()
				});
				if (n.series_type_changed && V(this, nt(t.title, n.series_type_changed)), e && !n.follow_new ? V(this, `${t.title} has no regular series to follow yet.`) : e && V(this, `New episodes of ${t.title} will download as they come out.`), this._selected !== t) return;
				this._show = {
					in_sonarr: n.in_sonarr,
					follow_new: n.follow_new
				}, this._episodes && this._episodeSeason && this._loadEpisodes(t.tmdb_id, this._episodeSeason.season_number);
			} catch (e) {
				V(this, `Couldn't change it: ${H(e)}`), this.requestUpdate();
			} finally {
				this._followBusy = !1;
			}
		}
	}
	_renderFollow(e) {
		return !this._picker || this._show === void 0 ? j : this._show === null ? k`<div class="message">Couldn't reach Sonarr for this show.</div>` : k`
      <div class="seasons options">
        <label class="row option">
          <input
            type="checkbox"
            .checked=${Ne(this._show.follow_new)}
            ?disabled=${this._followBusy}
            @change=${(e) => this._setFollowShow(e.target.checked)}
          />
          <span class="grow">
            Get new episodes
            ${this._followBusy ? k`<span class="hint busy">Checking how it's released and setting it up… This can take a
                  minute; it carries on if you leave.</span>` : k`<span class="hint">
                  Download new episodes of ${e.title} as they come out, including new series. Turning it off
                  also cancels upcoming episodes you picked.
                </span>`}
          </span>
        </label>
      </div>
    `;
	}
	render() {
		return this._config ? k`
      <ha-card .header=${this._config.title || void 0}>
        ${this._staleVersion ? k`<div class="stale">
              Card is out of date (server has ${this._staleVersion}).
              <button class="link" @click=${this._reload}>Reload</button>
            </div>` : j}
        ${this._selected && this._episodeSeason ? this._renderEpisodes(this._selected, this._episodeSeason) : this._selected ? this._renderDetail(this._selected) : this._renderSearch()}
      </ha-card>
    ` : j;
	}
	_renderSearch() {
		return k`
      <div class="search">
        <div class="field">
          <ha-icon icon="mdi:magnify"></ha-icon>
          <input
            type="search"
            enterkeyhint="search"
            autocomplete="off"
            placeholder="Search movies and TV"
            aria-label="Search movies and TV"
            .value=${this._query}
            @input=${this._onInput}
            @keydown=${this._onKeydown}
          />
          ${this._query ? k`<button class="icon" aria-label="Clear" @click=${this._clear}>
                <ha-icon icon="mdi:close"></ha-icon>
              </button>` : j}
        </div>
        <div class="chips" role="radiogroup" aria-label="Media type">
          ${et.filter((e) => e.value !== "waiting" || this._waitingOn).map((e) => k`<button
              class="chip ${e.value === this._filter ? "on" : ""}"
              role="radio"
              aria-checked=${e.value === this._filter}
              @click=${() => this._setFilter(e.value)}
            >
              ${e.label}
            </button>`)}
        </div>
      </div>
      ${this._renderResults()}
    `;
	}
	_renderResults() {
		return this._filter === "downloaded" ? this._renderLibrary() : this._filter === "waiting" ? this._renderWaiting() : this._showBrowse() ? this._renderBrowse() : this._error ? k`<div class="message error">${this._error}</div>` : this._loading && !this._results ? k`<div class="message">Searching…</div>` : this._results ? this._results.length ? k`
      <div class="grid ${this._loading ? "busy" : ""}">
        ${this._results.map((e) => this._renderTile(e))}
      </div>
    ` : k`<div class="message">No movies or shows found.</div>` : j;
	}
	_renderBrowse() {
		let e = tt.find((e) => e.value === this._browse).heading, t;
		return t = this._browseError ? k`<div class="message error">Couldn't load ${e.toLowerCase()} (${this._browseError}).</div>` : this._browseResults ? this._browseResults.length ? k`<div class="grid">${this._browseResults.map((e) => this._renderTile(e))}</div>` : k`<div class="message">Nothing to show.</div>` : k`<div class="message">Loading…</div>`, k`
      <div class="section">
        <span>${e}</span>
        <div class="chips small" role="radiogroup" aria-label="Browse">
          ${tt.map((e) => k`<button
              class="chip ${e.value === this._browse ? "on" : ""}"
              role="radio"
              aria-checked=${e.value === this._browse}
              @click=${() => this._setBrowse(e.value)}
            >
              ${e.label}
            </button>`)}
        </div>
      </div>
      ${t}
    `;
	}
	_renderLibrary() {
		let e;
		if (this._libraryError) e = k`<div class="message error">Couldn't load what's downloaded (${this._libraryError}).</div>`;
		else if (!this._library) e = k`<div class="message">Loading…</div>`;
		else {
			let t = q(this._library, this._query);
			e = t.length ? k`<div class="grid">${t.map((e) => this._renderTile(e))}</div>` : k`<div class="message">
            ${this._library.length ? `Nothing downloaded matches “${this._query.trim()}”.` : "Nothing downloaded yet."}
          </div>`;
		}
		return k`
      <div class="section stack">
        <span>Downloaded${this._library ? k` · ${q(this._library, this._query).length}` : j}</span>
        <span class="hint">Newest first. Tap one to remove it or get more episodes.</span>
      </div>
      ${e}
    `;
	}
	_renderWaiting() {
		if (this._waitingError) return k`<div class="message error">Couldn't load the Waiting list (${this._waitingError}).</div>`;
		if (!this._waiting) return k`<div class="message">Loading…</div>`;
		let e = q(this._waiting, this._query);
		return k`
      <div class="section stack">
        <span>Waiting · ${e.length}</span>
        <span class="hint">Wanted but not downloaded yet: what's out, what isn't, and when.</span>
      </div>
      ${e.length ? k`<div class="waiting">${e.map((e) => this._renderWaitingRow(e))}</div>` : k`<div class="message">
            ${this._waiting.length ? `Nothing waiting matches “${this._query.trim()}”.` : "Nothing waiting: everything wanted is downloaded."}
          </div>`}
    `;
	}
	_renderWaitingRow(e) {
		let t = this._checks[this._key(e)], n = t === "checking";
		return k`
      <div class="wrow">
        <button class="wposter" ?disabled=${!e.tmdb_id} @click=${() => this._openWaiting(e)} aria-label=${e.title}>
          ${e.poster_url ? k`<img src=${e.poster_url} alt="" loading="lazy" />` : k`<ha-icon icon=${e.media_type === "tv" ? "mdi:television-classic" : "mdi:movie-open"}></ha-icon>`}
        </button>
        <div class="wbody">
          <div class="wtitle">
            <span>${e.title}${e.year ? k` <span class="count">(${e.year})</span>` : j}</span>
            <span class="status inline w-${e.state}">${Ge(e)}</span>
          </div>
          <div class="hint">${Ke(e)}</div>
          ${typeof t == "object" ? k`<div class="wcheck">${qe(t)}</div>` : j}
          ${typeof t == "string" && !n ? k`<div class="wcheck error">${t}</div>` : j}
          ${e.state === "downloading" ? j : k`<div class="wactions">
                <button class="secondary small" ?disabled=${n} @click=${() => this._checkWaiting(e)}>
                  ${n ? "Checking…" : "Check now"}
                </button>
                ${e.state === "not_found" ? k`<button class="secondary small" @click=${() => this._searchWaiting(e)}>Search again</button>` : j}
              </div>`}
        </div>
      </div>
    `;
	}
	_renderTile(e) {
		let t = W(e.status);
		return k`
      <button class="tile" @click=${() => this._open(e)} aria-label="${e.title} ${e.year ?? ""}">
        <div class="poster">
          ${e.poster_url ? k`<img src=${e.poster_url} alt="" loading="lazy" />` : k`<ha-icon icon=${e.media_type === "tv" ? "mdi:television-classic" : "mdi:movie-open"}></ha-icon>`}
          ${t ? k`<span class="status ${e.status}">${t}</span>` : j}
          <span class="kind">${e.media_type === "tv" ? "TV" : "Movie"}</span>
        </div>
        <div class="title">${e.title}</div>
        <div class="year">${e.year ?? ""}</div>
      </button>
    `;
	}
	_renderDetail(e) {
		let t = W(e.status), n = e.media_type === "tv", r = n ? Le(e.status) && (!this._seasons || this._chosen.size > 0) : U(e.status);
		return k`
      <div class="detail">
        <button class="back" @click=${this._back}>
          <ha-icon icon="mdi:arrow-left"></ha-icon> Back
        </button>
        <div class="head">
          ${e.poster_url ? k`<img class="thumb" src=${e.poster_url} alt="" />` : j}
          <div>
            <h2>${e.title}</h2>
            <div class="meta">
              ${e.year ?? ""} · ${n ? "TV show" : "Movie"}
              ${t ? k`<span class="status inline ${e.status}">${t}</span>` : j}
            </div>
            ${this._release && Je(this._release, e.media_type, (/* @__PURE__ */ new Date()).toISOString().slice(0, 10)) ? k`<div class="release">${Je(this._release, e.media_type, (/* @__PURE__ */ new Date()).toISOString().slice(0, 10))}</div>` : j}
            ${this._config.show_remove && Ie(e.status) && !this._confirmRemove ? k`<button class="danger small head-remove" @click=${this._remove}>
                  ${n ? "Remove all…" : "Remove…"}
                </button>` : j}
          </div>
        </div>
        ${this._config.show_remove && Ie(e.status) && this._confirmRemove ? this._renderRemove(e) : j}
        ${e.overview ? k`<p class="overview">${e.overview}</p>` : j}
        ${n ? this._renderFollow(e) : j}
        ${n ? this._renderSeasons() : j}
        ${this._config.show_4k && r ? k`<label class="row">
              <input type="checkbox" .checked=${this._is4k} @change=${(e) => this._is4k = e.target.checked} />
              Request in 4K
            </label>` : j}
        <button class="primary" ?disabled=${!r || this._requesting} @click=${this._request}>
          ${this._requesting ? "Requesting…" : r ? "Request" : t ?? "Unavailable"}
        </button>
      </div>
    `;
	}
	_renderRemove(e) {
		return k`
      <div class="confirm" role="alert">Delete ${e.media_type === "tv" ? `${e.title} and all its downloaded episodes` : `${e.title} and its file`}? This can't be undone.</div>
      <div class="confirm-row">
        <button class="secondary" ?disabled=${this._removing} @click=${() => this._confirmRemove = !1}>
          Cancel
        </button>
        <button class="danger solid" ?disabled=${this._removing} @click=${this._remove}>
          ${this._removing ? "Removing…" : "Delete files"}
        </button>
      </div>
    `;
	}
	_renderSeasons() {
		if (this._seasonsError) return k`<div class="message error">Couldn't load seasons (${this._seasonsError}). Request will ask for all.</div>`;
		if (!this._seasons) return k`<div class="message">Loading seasons…</div>`;
		let e = G(this._seasons);
		return k`
      <div class="seasons">
        <div class="seasons-head">
          <span>Seasons</span>
          ${e.length > 1 ? k`<button class="link" @click=${this._toggleAllSeasons}>
                ${this._chosen.size === e.length ? "Select none" : "Select all"}
              </button>` : j}
        </div>
        ${this._seasons.map((e) => {
			let t = U(e.status), n = W(e.status);
			return k`<label class="row season ${t ? "" : "done"}">
            <input
              type="checkbox"
              .checked=${!t || this._chosen.has(e.season_number)}
              ?disabled=${!t}
              @change=${() => this._toggleSeason(e.season_number)}
            />
            <span class="grow">${e.name}</span>
            ${n ? k`<span class="status inline ${e.status}">${n}</span>` : j}
            ${this._picker ? k`<button class="link episodes-link" @click=${(t) => this._openEpisodes(e, t)}>
                  Episodes
                </button>` : j}
          </label>`;
		})}
      </div>
    `;
	}
	_renderEpisodes(e, t) {
		let n = this._episodes, r;
		if (this._episodesError) r = k`<div class="message error">Couldn't load episodes (${this._episodesError}).</div>`;
		else if (!n) r = k`<div class="message">Loading episodes from Sonarr…</div>`;
		else {
			let e = ze(n.episodes), t = this._picked.size;
			r = k`
        <div class="seasons">
          <div class="seasons-head">
            <span>${n.episodes.length} episodes</span>
            ${e.length > 1 ? k`<button class="link" @click=${this._toggleAllPicks}>
                  ${t === e.length ? "Select none" : `Select all ${e.length}`}
                </button>` : j}
          </div>
          ${n.episodes.length ? n.episodes.map((e) => {
				let t = Re(e), n = Be(e);
				return k`<label class="row season episode ${t ? "" : "done"}">
                  <input
                    type="checkbox"
                    .checked=${t ? this._picked.has(e.id) : e.status !== "not_aired" || e.monitored}
                    ?disabled=${!t}
                    @change=${() => this._togglePick(e.id)}
                  />
                  <span class="grow">
                    <span class="ep-title">${e.episode_number}. ${e.title || `Episode ${e.episode_number}`}</span>
                    <span class="hint">${Ve(e.air_date)}</span>
                  </span>
                  ${n ? k`<span class="status inline ep ${e.status}">${n}</span>` : j}
                  ${this._config.show_remove && e.status === "downloaded" && this._confirmRemoveEp !== e.id ? k`<button class="link ep-remove" @click=${(t) => this._askRemoveEpisode(e.id, t)}>
                        Remove
                      </button>` : j}
                </label>
                ${this._confirmRemoveEp === e.id ? k`<div class="ep-confirm" role="alert">
                      <span class="grow">Delete episode ${e.episode_number}'s file? This can't be undone.</span>
                      <button class="secondary small" ?disabled=${this._pickerBusy} @click=${() => this._confirmRemoveEp = void 0}>
                        Cancel
                      </button>
                      <button class="danger solid small" ?disabled=${this._pickerBusy} @click=${() => this._removeEpisode(e)}>
                        ${this._pickerBusy ? "Deleting…" : "Delete file"}
                      </button>
                    </div>` : j}`;
			}) : k`<div class="message">Sonarr lists no episodes for this season yet.</div>`}
        </div>
        ${t > 20 ? k`<div class="warn">That's ${t} episodes. Check there's room before downloading.</div>` : j}
        <button class="primary" ?disabled=${!t || this._pickerBusy} @click=${this._download}>
          ${this._downloading ? "Searching… (carries on if you leave)" : this._pickerBusy ? "Working…" : t ? `Download ${t} episode${t === 1 ? "" : "s"}` : "Pick episodes to download"}
        </button>
      `;
		}
		return k`
      <div class="detail">
        <button class="back" @click=${this._closeEpisodes}>
          <ha-icon icon="mdi:arrow-left"></ha-icon> ${e.title}
        </button>
        <div class="ep-head">
          <h2>${t.name}</h2>
          <div class="meta">Episodes from Sonarr</div>
        </div>
        ${r}
      </div>
    `;
	}
};
Y = $, Y.properties = {
	hass: { attribute: !1 },
	_config: { state: !0 },
	_query: { state: !0 },
	_filter: { state: !0 },
	_results: { state: !0 },
	_browse: { state: !0 },
	_browseResults: { state: !0 },
	_browseError: { state: !0 },
	_loading: { state: !0 },
	_error: { state: !0 },
	_selected: { state: !0 },
	_seasons: { state: !0 },
	_seasonsError: { state: !0 },
	_chosen: { state: !0 },
	_is4k: { state: !0 },
	_requesting: { state: !0 },
	_confirmRemove: { state: !0 },
	_removing: { state: !0 },
	_staleVersion: { state: !0 },
	_picker: { state: !0 },
	_episodeSeason: { state: !0 },
	_episodes: { state: !0 },
	_episodesError: { state: !0 },
	_picked: { state: !0 },
	_pickerBusy: { state: !0 },
	_confirmRemoveEp: { state: !0 },
	_downloading: { state: !0 },
	_followBusy: { state: !0 },
	_show: { state: !0 },
	_waiting: { state: !0 },
	_release: { state: !0 },
	_waitingError: { state: !0 },
	_checks: { state: !0 },
	_waitingOn: { state: !0 },
	_library: { state: !0 },
	_libraryError: { state: !0 }
}, Y.styles = o`
    :host {
      --js-gap: 12px;
      --js-radius: var(--ha-card-border-radius, 12px);
    }
    .stale {
      margin: var(--js-gap);
      padding: 8px 12px;
      border-radius: 8px;
      background: var(--warning-color, #ffa600);
      color: var(--text-primary-color, #fff);
    }
    .search {
      padding: var(--js-gap) var(--js-gap) 0;
    }
    .field {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0 8px 0 12px;
      border-radius: 24px;
      background: var(--secondary-background-color);
      color: var(--secondary-text-color);
    }
    input[type="search"] {
      flex: 1;
      min-width: 0;
      height: 44px;
      border: 0;
      outline: 0;
      background: transparent;
      color: var(--primary-text-color);
      font: inherit;
      font-size: 16px; /* Below 16px iOS zooms the page on focus. */
    }
    input[type="search"]::-webkit-search-cancel-button {
      display: none;
    }
    button {
      font: inherit;
      color: inherit;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }
    .icon {
      display: grid;
      place-items: center;
      width: 36px;
      height: 36px;
      border: 0;
      border-radius: 50%;
      background: none;
    }
    .chips {
      display: flex;
      gap: 8px;
      padding: 10px 0 4px;
    }
    .chip {
      padding: 6px 14px;
      border-radius: 16px;
      border: 1px solid var(--divider-color);
      background: none;
      color: var(--primary-text-color);
    }
    .chip.on {
      background: var(--primary-color);
      border-color: var(--primary-color);
      color: var(--text-primary-color, #fff);
    }
    .message {
      padding: var(--js-gap);
      color: var(--secondary-text-color);
    }
    .message.error {
      color: var(--error-color);
    }
    .section {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: var(--js-gap) var(--js-gap) 0;
      font-weight: 500;
      color: var(--secondary-text-color);
    }
    .chips.small {
      padding: 0;
    }
    .chips.small .chip {
      padding: 3px 10px;
      font-size: 13px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
      gap: var(--js-gap);
      padding: var(--js-gap);
      transition: opacity 0.2s;
    }
    .grid.busy {
      opacity: 0.5;
    }
    .tile {
      display: flex;
      flex-direction: column;
      padding: 0;
      border: 0;
      background: none;
      text-align: start;
      min-width: 0;
    }
    .poster {
      position: relative;
      aspect-ratio: 2 / 3;
      border-radius: 8px;
      overflow: hidden;
      display: grid;
      place-items: center;
      background: var(--secondary-background-color);
      color: var(--secondary-text-color);
      --mdc-icon-size: 40px;
    }
    .poster img {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .status,
    .kind {
      position: absolute;
      padding: 2px 6px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 500;
      line-height: 16px;
    }
    .status {
      top: 6px;
      right: 6px;
      background: var(--info-color, #039be5);
      color: #fff;
    }
    .status.available {
      background: var(--success-color, #43a047);
    }
    .status.partially_available {
      background: var(--warning-color, #ffa600);
    }
    .status.blacklisted {
      background: var(--error-color, #db4437);
    }
    .status.inline {
      position: static;
      margin-inline-start: 6px;
    }
    .kind {
      bottom: 6px;
      left: 6px;
      background: rgba(0, 0, 0, 0.6);
      color: #fff;
    }
    .title {
      margin-top: 6px;
      font-size: 13px;
      font-weight: 500;
      color: var(--primary-text-color);
      overflow: hidden;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
    }
    .year {
      font-size: 12px;
      color: var(--secondary-text-color);
    }
    .detail {
      display: flex;
      flex-direction: column;
      gap: var(--js-gap);
      padding: var(--js-gap);
    }
    .back {
      align-self: flex-start;
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 6px 8px 6px 4px;
      border: 0;
      border-radius: 8px;
      background: none;
      color: var(--primary-color);
    }
    .head {
      display: flex;
      gap: var(--js-gap);
      align-items: flex-start;
    }
    .thumb {
      width: 88px;
      aspect-ratio: 2 / 3;
      object-fit: cover;
      border-radius: 8px;
      flex: none;
    }
    h2 {
      margin: 0 0 4px;
      font-size: 20px;
      line-height: 1.25;
      font-weight: 500;
      color: var(--primary-text-color);
    }
    .meta,
    .count {
      color: var(--secondary-text-color);
      font-size: 14px;
    }
    .overview {
      margin: 0;
      color: var(--primary-text-color);
      line-height: 1.45;
    }
    .seasons {
      border: 1px solid var(--divider-color);
      border-radius: 8px;
      overflow: hidden;
    }
    .seasons-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      font-weight: 500;
      background: var(--secondary-background-color);
    }
    .row {
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 44px;
    }
    .season {
      padding: 0 12px;
      border-top: 1px solid var(--divider-color);
    }
    .season.done {
      color: var(--secondary-text-color);
    }
    .episodes-link {
      flex: none;
      font-size: 14px;
    }
    .option {
      padding: 6px 12px;
    }
    .option + .option {
      border-top: 1px solid var(--divider-color);
    }
    .hint {
      display: block;
      color: var(--secondary-text-color);
      font-size: 12px;
      line-height: 1.3;
    }
    .episode {
      padding-block: 6px;
    }
    .ep-title {
      display: block;
      line-height: 1.3;
    }
    .ep-head h2 {
      margin: 0;
    }
    .status.ep {
      flex: none;
    }
    .status.downloaded {
      background: var(--success-color, #43a047);
    }
    .status.not_aired {
      background: var(--secondary-text-color, #727272);
    }
    .head-remove {
      margin-top: 10px;
      align-self: flex-start;
    }
    .link.ep-remove {
      flex: none;
      font-size: 14px;
      color: var(--error-color, #db4437);
    }
    .ep-confirm {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      padding: 8px 12px 10px;
      color: var(--error-color, #db4437);
      font-size: 14px;
      line-height: 1.35;
    }
    .ep-confirm .grow {
      flex-basis: 100%;
    }
    .small {
      height: 36px;
      padding: 0 16px;
      font-size: 14px;
    }
    .section.stack {
      flex-direction: column;
      align-items: flex-start;
      gap: 2px;
    }
    .section.stack .hint {
      font-weight: 400;
    }
    .hint.busy {
      color: var(--primary-color);
    }
    .chips {
      flex-wrap: wrap;
    }
    .waiting {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 8px var(--js-gap) var(--js-gap);
    }
    .wrow {
      display: flex;
      gap: 12px;
      padding: 10px;
      border: 1px solid var(--divider-color);
      border-radius: 10px;
    }
    .wposter {
      flex: none;
      width: 56px;
      height: 84px;
      padding: 0;
      border: 0;
      border-radius: 6px;
      overflow: hidden;
      background: var(--secondary-background-color);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .wposter img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .wbody {
      min-width: 0;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .wtitle {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
      font-weight: 500;
      line-height: 1.3;
    }
    .wtitle .status {
      flex: none;
    }
    .status.w-not_out {
      background: var(--secondary-text-color, #727272);
    }
    .status.w-not_found {
      background: var(--warning-color, #ffa600);
    }
    .wcheck {
      font-size: 13px;
      line-height: 1.35;
    }
    .wcheck.error {
      color: var(--error-color, #db4437);
    }
    .wactions {
      display: flex;
      gap: 8px;
      margin-top: 4px;
    }
    .release {
      margin-top: 4px;
      font-size: 13px;
      color: var(--secondary-text-color);
    }
    .warn {
      color: var(--warning-color, #ffa600);
      line-height: 1.4;
    }
    .row input {
      width: 20px;
      height: 20px;
      accent-color: var(--primary-color);
    }
    .grow {
      flex: 1;
    }
    .link {
      border: 0;
      background: none;
      color: var(--primary-color);
      padding: 4px;
    }
    .primary {
      height: 44px;
      border: 0;
      border-radius: 22px;
      background: var(--primary-color);
      color: var(--text-primary-color, #fff);
      font-weight: 500;
    }
    .danger,
    .secondary {
      height: 44px;
      border-radius: 22px;
      font-weight: 500;
      background: none;
    }
    .danger {
      border: 1px solid var(--error-color, #db4437);
      color: var(--error-color, #db4437);
    }
    .danger.solid {
      background: var(--error-color, #db4437);
      color: #fff;
    }
    .secondary {
      border: 1px solid var(--divider-color);
      color: var(--primary-text-color);
    }
    .confirm {
      color: var(--error-color, #db4437);
      line-height: 1.4;
    }
    .confirm-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: var(--js-gap);
    }
    .danger[disabled],
    .secondary[disabled] {
      opacity: 0.6;
      cursor: default;
    }
    .primary[disabled] {
      background: var(--disabled-color, #bdbdbd);
      cursor: default;
    }
  `, customElements.get("jellyseerr-search-card") || (customElements.define("jellyseerr-search-card", $), window.customCards = window.customCards ?? [], window.customCards.push({
	type: "jellyseerr-search-card",
	name: "Jellyseerr Search",
	description: "Search movies and TV shows and request them through Jellyseerr.",
	preview: !1
}));
//#endregion
export { Ye as CARD_VERSION, $ as JellyseerrSearchCard };
