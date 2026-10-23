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
})(e) : e, { is: l, defineProperty: u, getOwnPropertyDescriptor: d, getOwnPropertyNames: ee, getOwnPropertySymbols: te, getPrototypeOf: ne } = Object, f = globalThis, p = f.trustedTypes, re = p ? p.emptyScript : "", ie = f.reactiveElementPolyfillSupport, m = (e, t) => e, h = {
	toAttribute(e, t) {
		switch (t) {
			case Boolean:
				e = e ? re : null;
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
}, g = (e, t) => !l(e, t), _ = {
	attribute: !0,
	type: String,
	converter: h,
	reflect: !1,
	useDefault: !1,
	hasChanged: g
};
Symbol.metadata ??= Symbol("metadata"), f.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
var v = class extends HTMLElement {
	static addInitializer(e) {
		this._$Ei(), (this.l ??= []).push(e);
	}
	static get observedAttributes() {
		return this.finalize(), this._$Eh && [...this._$Eh.keys()];
	}
	static createProperty(e, t = _) {
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
		return this.elementProperties.get(e) ?? _;
	}
	static _$Ei() {
		if (this.hasOwnProperty(m("elementProperties"))) return;
		let e = ne(this);
		e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
	}
	static finalize() {
		if (this.hasOwnProperty(m("finalized"))) return;
		if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(m("properties"))) {
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
			let i = (n.converter?.toAttribute === void 0 ? h : n.converter).toAttribute(t, n.type);
			this._$Em = e, i == null ? this.removeAttribute(r) : this.setAttribute(r, i), this._$Em = null;
		}
	}
	_$AK(e, t) {
		let n = this.constructor, r = n._$Eh.get(e);
		if (r !== void 0 && this._$Em !== r) {
			let e = n.getPropertyOptions(r), i = typeof e.converter == "function" ? { fromAttribute: e.converter } : e.converter?.fromAttribute === void 0 ? h : e.converter;
			this._$Em = r;
			let a = i.fromAttribute(t, e.type);
			this[r] = a ?? this._$Ej?.get(r) ?? a, this._$Em = null;
		}
	}
	requestUpdate(e, t, n, r = !1, i) {
		if (e !== void 0) {
			let a = this.constructor;
			if (!1 === r && (i = this[e]), n ??= a.getPropertyOptions(e), !((n.hasChanged ?? g)(i, t) || n.useDefault && n.reflect && i === this._$Ej?.get(e) && !this.hasAttribute(a._$Eu(e, n)))) return;
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
v.elementStyles = [], v.shadowRootOptions = { mode: "open" }, v[m("elementProperties")] = /* @__PURE__ */ new Map(), v[m("finalized")] = /* @__PURE__ */ new Map(), ie?.({ ReactiveElement: v }), (f.reactiveElementVersions ??= []).push("2.1.2");
//#endregion
//#region node_modules/lit-html/lit-html.js
var y = globalThis, ae = (e) => e, b = y.trustedTypes, oe = b ? b.createPolicy("lit-html", { createHTML: (e) => e }) : void 0, se = "$lit$", x = `lit$${Math.random().toFixed(9).slice(2)}$`, S = "?" + x, ce = `<${S}>`, C = document, w = () => C.createComment(""), T = (e) => e === null || typeof e != "object" && typeof e != "function", E = Array.isArray, le = (e) => E(e) || typeof e?.[Symbol.iterator] == "function", D = "[ 	\n\f\r]", O = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, k = /-->/g, ue = />/g, A = RegExp(`>|${D}(?:([^\\s"'>=/]+)(${D}*=${D}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`, "g"), de = /'/g, fe = /"/g, j = /^(?:script|style|textarea|title)$/i, M = ((e) => (t, ...n) => ({
	_$litType$: e,
	strings: t,
	values: n
}))(1), N = Symbol.for("lit-noChange"), P = Symbol.for("lit-nothing"), F = /* @__PURE__ */ new WeakMap(), I = C.createTreeWalker(C, 129);
function L(e, t) {
	if (!E(e) || !e.hasOwnProperty("raw")) throw Error("invalid template strings array");
	return oe === void 0 ? t : oe.createHTML(t);
}
var pe = (e, t) => {
	let n = e.length - 1, r = [], i, a = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", o = O;
	for (let t = 0; t < n; t++) {
		let n = e[t], s, c, l = -1, u = 0;
		for (; u < n.length && (o.lastIndex = u, c = o.exec(n), c !== null);) u = o.lastIndex, o === O ? c[1] === "!--" ? o = k : c[1] === void 0 ? c[2] === void 0 ? c[3] !== void 0 && (o = A) : (j.test(c[2]) && (i = RegExp("</" + c[2], "g")), o = A) : o = ue : o === A ? c[0] === ">" ? (o = i ?? O, l = -1) : c[1] === void 0 ? l = -2 : (l = o.lastIndex - c[2].length, s = c[1], o = c[3] === void 0 ? A : c[3] === "\"" ? fe : de) : o === fe || o === de ? o = A : o === k || o === ue ? o = O : (o = A, i = void 0);
		let d = o === A && e[t + 1].startsWith("/>") ? " " : "";
		a += o === O ? n + ce : l >= 0 ? (r.push(s), n.slice(0, l) + se + n.slice(l) + x + d) : n + x + (l === -2 ? t : d);
	}
	return [L(e, a + (e[n] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), r];
}, R = class e {
	constructor({ strings: t, _$litType$: n }, r) {
		let i;
		this.parts = [];
		let a = 0, o = 0, s = t.length - 1, c = this.parts, [l, u] = pe(t, n);
		if (this.el = e.createElement(l, r), I.currentNode = this.el.content, n === 2 || n === 3) {
			let e = this.el.content.firstChild;
			e.replaceWith(...e.childNodes);
		}
		for (; (i = I.nextNode()) !== null && c.length < s;) {
			if (i.nodeType === 1) {
				if (i.hasAttributes()) for (let e of i.getAttributeNames()) if (e.endsWith(se)) {
					let t = u[o++], n = i.getAttribute(e).split(x), r = /([.?@])?(.*)/.exec(t);
					c.push({
						type: 1,
						index: a,
						name: r[2],
						strings: n,
						ctor: r[1] === "." ? he : r[1] === "?" ? ge : r[1] === "@" ? _e : V
					}), i.removeAttribute(e);
				} else e.startsWith(x) && (c.push({
					type: 6,
					index: a
				}), i.removeAttribute(e));
				if (j.test(i.tagName)) {
					let e = i.textContent.split(x), t = e.length - 1;
					if (t > 0) {
						i.textContent = b ? b.emptyScript : "";
						for (let n = 0; n < t; n++) i.append(e[n], w()), I.nextNode(), c.push({
							type: 2,
							index: ++a
						});
						i.append(e[t], w());
					}
				}
			} else if (i.nodeType === 8) {
				if (i.data === S) c.push({
					type: 2,
					index: a
				});
				else {
					let e = -1;
					for (; (e = i.data.indexOf(x, e + 1)) !== -1;) c.push({
						type: 7,
						index: a
					}), e += x.length - 1;
				}
			}
			a++;
		}
	}
	static createElement(e, t) {
		let n = C.createElement("template");
		return n.innerHTML = e, n;
	}
};
function z(e, t, n = e, r) {
	if (t === N) return t;
	let i = r === void 0 ? n._$Cl : n._$Co?.[r], a = T(t) ? void 0 : t._$litDirective$;
	return i?.constructor !== a && (i?._$AO?.(!1), a === void 0 ? i = void 0 : (i = new a(e), i._$AT(e, n, r)), r === void 0 ? n._$Cl = i : (n._$Co ??= [])[r] = i), i !== void 0 && (t = z(e, i._$AS(e, t.values), i, r)), t;
}
var me = class {
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
		let { el: { content: t }, parts: n } = this._$AD, r = (e?.creationScope ?? C).importNode(t, !0);
		I.currentNode = r;
		let i = I.nextNode(), a = 0, o = 0, s = n[0];
		for (; s !== void 0;) {
			if (a === s.index) {
				let t;
				s.type === 2 ? t = new B(i, i.nextSibling, this, e) : s.type === 1 ? t = new s.ctor(i, s.name, s.strings, this, e) : s.type === 6 && (t = new ve(i, this, e)), this._$AV.push(t), s = n[++o];
			}
			a !== s?.index && (i = I.nextNode(), a++);
		}
		return I.currentNode = C, r;
	}
	p(e) {
		let t = 0;
		for (let n of this._$AV) n !== void 0 && (n.strings === void 0 ? n._$AI(e[t]) : (n._$AI(e, n, t), t += n.strings.length - 2)), t++;
	}
}, B = class e {
	get _$AU() {
		return this._$AM?._$AU ?? this._$Cv;
	}
	constructor(e, t, n, r) {
		this.type = 2, this._$AH = P, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = n, this.options = r, this._$Cv = r?.isConnected ?? !0;
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
		e = z(this, e, t), T(e) ? e === P || e == null || e === "" ? (this._$AH !== P && this._$AR(), this._$AH = P) : e !== this._$AH && e !== N && this._(e) : e._$litType$ === void 0 ? e.nodeType === void 0 ? le(e) ? this.k(e) : this._(e) : this.T(e) : this.$(e);
	}
	O(e) {
		return this._$AA.parentNode.insertBefore(e, this._$AB);
	}
	T(e) {
		this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
	}
	_(e) {
		this._$AH !== P && T(this._$AH) ? this._$AA.nextSibling.data = e : this.T(C.createTextNode(e)), this._$AH = e;
	}
	$(e) {
		let { values: t, _$litType$: n } = e, r = typeof n == "number" ? this._$AC(e) : (n.el === void 0 && (n.el = R.createElement(L(n.h, n.h[0]), this.options)), n);
		if (this._$AH?._$AD === r) this._$AH.p(t);
		else {
			let e = new me(r, this), n = e.u(this.options);
			e.p(t), this.T(n), this._$AH = e;
		}
	}
	_$AC(e) {
		let t = F.get(e.strings);
		return t === void 0 && F.set(e.strings, t = new R(e)), t;
	}
	k(t) {
		E(this._$AH) || (this._$AH = [], this._$AR());
		let n = this._$AH, r, i = 0;
		for (let a of t) i === n.length ? n.push(r = new e(this.O(w()), this.O(w()), this, this.options)) : r = n[i], r._$AI(a), i++;
		i < n.length && (this._$AR(r && r._$AB.nextSibling, i), n.length = i);
	}
	_$AR(e = this._$AA.nextSibling, t) {
		for (this._$AP?.(!1, !0, t); e !== this._$AB;) {
			let t = ae(e).nextSibling;
			ae(e).remove(), e = t;
		}
	}
	setConnected(e) {
		this._$AM === void 0 && (this._$Cv = e, this._$AP?.(e));
	}
}, V = class {
	get tagName() {
		return this.element.tagName;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	constructor(e, t, n, r, i) {
		this.type = 1, this._$AH = P, this._$AN = void 0, this.element = e, this.name = t, this._$AM = r, this.options = i, n.length > 2 || n[0] !== "" || n[1] !== "" ? (this._$AH = Array(n.length - 1).fill(/* @__PURE__ */ new String()), this.strings = n) : this._$AH = P;
	}
	_$AI(e, t = this, n, r) {
		let i = this.strings, a = !1;
		if (i === void 0) e = z(this, e, t, 0), a = !T(e) || e !== this._$AH && e !== N, a && (this._$AH = e);
		else {
			let r = e, o, s;
			for (e = i[0], o = 0; o < i.length - 1; o++) s = z(this, r[n + o], t, o), s === N && (s = this._$AH[o]), a ||= !T(s) || s !== this._$AH[o], s === P ? e = P : e !== P && (e += (s ?? "") + i[o + 1]), this._$AH[o] = s;
		}
		a && !r && this.j(e);
	}
	j(e) {
		e === P ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
	}
}, he = class extends V {
	constructor() {
		super(...arguments), this.type = 3;
	}
	j(e) {
		this.element[this.name] = e === P ? void 0 : e;
	}
}, ge = class extends V {
	constructor() {
		super(...arguments), this.type = 4;
	}
	j(e) {
		this.element.toggleAttribute(this.name, !!e && e !== P);
	}
}, _e = class extends V {
	constructor(e, t, n, r, i) {
		super(e, t, n, r, i), this.type = 5;
	}
	_$AI(e, t = this) {
		if ((e = z(this, e, t, 0) ?? P) === N) return;
		let n = this._$AH, r = e === P && n !== P || e.capture !== n.capture || e.once !== n.once || e.passive !== n.passive, i = e !== P && (n === P || r);
		r && this.element.removeEventListener(this.name, this, n), i && this.element.addEventListener(this.name, this, e), this._$AH = e;
	}
	handleEvent(e) {
		typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, e) : this._$AH.handleEvent(e);
	}
}, ve = class {
	constructor(e, t, n) {
		this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = n;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	_$AI(e) {
		z(this, e);
	}
}, ye = y.litHtmlPolyfillSupport;
ye?.(R, B), (y.litHtmlVersions ??= []).push("3.3.3");
var be = (e, t, n) => {
	let r = n?.renderBefore ?? t, i = r._$litPart$;
	if (i === void 0) {
		let e = n?.renderBefore ?? null;
		r._$litPart$ = i = new B(t.insertBefore(w(), e), e, void 0, n ?? {});
	}
	return i._$AI(e), i;
}, H = globalThis, U = class extends v {
	constructor() {
		super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
	}
	createRenderRoot() {
		let e = super.createRenderRoot();
		return this.renderOptions.renderBefore ??= e.firstChild, e;
	}
	update(e) {
		let t = this.render();
		this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = be(t, this.renderRoot, this.renderOptions);
	}
	connectedCallback() {
		super.connectedCallback(), this._$Do?.setConnected(!0);
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this._$Do?.setConnected(!1);
	}
	render() {
		return N;
	}
};
U._$litElement$ = !0, U.finalized = !0, H.litElementHydrateSupport?.({ LitElement: U });
var xe = H.litElementPolyfillSupport;
xe?.({ LitElement: U }), (H.litElementVersions ??= []).push("4.2.2");
//#endregion
//#region src/ha.ts
function Se(e, t, n) {
	e.dispatchEvent(new CustomEvent(t, {
		detail: n,
		bubbles: !0,
		composed: !0
	}));
}
function W(e, t) {
	Se(e, "hass-notification", { message: t });
}
function G(e) {
	return e && typeof e == "object" && "message" in e ? String(e.message) : String(e);
}
//#endregion
//#region src/logic.ts
var Ce = /* @__PURE__ */ new Set([
	"not_requested",
	"unknown",
	"deleted"
]);
function K(e) {
	return Ce.has(e);
}
function q(e) {
	switch (e) {
		case "pending": return "Requested";
		case "processing": return "Processing";
		case "partially_available": return "Partial";
		case "available": return "Available";
		case "blacklisted": return "Blocked";
		default: return null;
	}
}
function we(e) {
	return e === "available" || e === "partially_available" || e === "processing";
}
function J(e) {
	return e.filter((e) => K(e.status)).map((e) => e.season_number);
}
function Te(e) {
	return K(e) || e === "partially_available";
}
function Ee(e) {
	return e.status === "missing" || e.status === "not_aired" && !e.monitored;
}
function De(e) {
	return e.filter(Ee).map((e) => e.id);
}
function Oe(e) {
	switch (e.status) {
		case "downloaded": return "Downloaded";
		case "downloading": return "Downloading";
		case "wanted": return "Not found yet";
		case "not_aired": return e.monitored ? "When it airs" : "Not aired";
		default: return null;
	}
}
function ke(e) {
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
var Y = class {
	constructor() {
		this._seq = 0;
	}
	next() {
		let e = ++this._seq;
		return () => e === this._seq;
	}
}, X, Ae = "0.5.4", Z = "jellyseerr_search", je = 400, Q = 2, Me = 36e5, Ne = [2e4, 6e4], Pe = !1, Fe = [
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
	}
], Ie = [{
	value: "trending",
	label: "Trending",
	heading: "Trending today"
}, {
	value: "popular",
	label: "Popular",
	heading: "Popular"
}], $ = class extends U {
	constructor() {
		super(), this._latestSearch = new Y(), this._latestSeasons = new Y(), this._latestBrowse = new Y(), this._latestEpisodes = new Y(), this._refreshTimers = [], this._browseAt = 0, this._query = "", this._filter = "all", this._browse = "trending", this._loading = !1, this._chosen = /* @__PURE__ */ new Set(), this._is4k = !1, this._requesting = !1, this._confirmRemove = !1, this._removing = !1, this._picker = !1, this._picked = /* @__PURE__ */ new Set(), this._pickerBusy = !1;
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
					selector: { config_entry: { integration: Z } }
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
		if (e.media_type && !Fe.some((t) => t.value === e.media_type)) throw Error("media_type must be all, movie or tv");
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
		e.has("hass") && this.hass && !Pe && (Pe = !0, this._checkVersion()), e.has("hass") && this.hass && this._browseDue() && this._loadBrowse();
	}
	async _checkVersion() {
		try {
			let { version: e } = await this.hass.callWS({ type: `${Z}/version` });
			e !== "0.5.4" && (this._staleVersion = e);
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
	_showBrowse() {
		return this._config.show_trending !== !1 && this._query.trim().length < Q;
	}
	_browseDue() {
		return !this._showBrowse() || this._selected ? !1 : this._browseKey !== `${this._browse}/${this._filter}` || Date.now() - this._browseAt > Me;
	}
	async _loadBrowse() {
		let e = this._latestBrowse.next(), t = `${this._browse}/${this._filter}`;
		this._browseKey !== t && (this._browseResults = void 0), this._browseKey = t, this._browseAt = Date.now(), this._browseError = void 0;
		try {
			let { results: t } = await this.hass.callWS({
				type: `${Z}/${this._browse}`,
				media_type: this._filter,
				...this._entry()
			});
			e() && (this._browseResults = t);
		} catch (t) {
			e() && (this._browseError = G(t));
		}
	}
	_setBrowse(e) {
		e !== this._browse && (this._browse = e, this._browseDue() && this._loadBrowse());
	}
	_onInput(e) {
		this._query = e.target.value, clearTimeout(this._debounce), this._debounce = setTimeout(() => void this._search(), je);
	}
	_onKeydown(e) {
		e.key === "Enter" && (clearTimeout(this._debounce), e.target.blur(), this._search());
	}
	_clear() {
		this._leaveShow(), clearTimeout(this._debounce), this._latestSearch.next(), this._query = "", this._results = void 0, this._error = void 0, this._loading = !1, this._selected = void 0;
	}
	_setFilter(e) {
		e !== this._filter && (this._filter = e, this._query.trim().length >= Q ? this._search() : this._browseDue() && this._loadBrowse());
	}
	async _search() {
		let e = this._query.trim();
		if (e.length < Q) {
			this._latestSearch.next(), this._results = void 0, this._loading = !1;
			return;
		}
		let t = this._latestSearch.next();
		this._loading = !0, this._error = void 0;
		try {
			let { results: n } = await this.hass.callWS({
				type: `${Z}/search`,
				query: e,
				media_type: this._filter,
				...this._entry()
			});
			if (!t()) return;
			this._results = n, this._selected = void 0;
		} catch (e) {
			t() && (this._error = G(e));
		} finally {
			t() && (this._loading = !1);
		}
	}
	_open(e) {
		this._leaveShow(), this._selected = e, this._seasons = void 0, this._seasonsError = void 0, this._chosen = /* @__PURE__ */ new Set(), this._is4k = !1, this._confirmRemove = !1, this._picker = !1, this._closeEpisodes(), e.media_type === "tv" && this._loadSeasons(e.tmdb_id);
	}
	async _loadSeasons(e) {
		let t = this._latestSeasons.next();
		try {
			let { seasons: n, episode_picker: r } = await this.hass.callWS({
				type: `${Z}/seasons`,
				tmdb_id: e,
				...this._entry()
			});
			if (!t()) return;
			this._seasons = n, this._picker = !!r, this._chosen = new Set(J(n));
		} catch (e) {
			t() && (this._seasonsError = G(e));
		}
	}
	_toggleSeason(e) {
		let t = new Set(this._chosen);
		t.has(e) ? t.delete(e) : t.add(e), this._chosen = t;
	}
	_toggleAllSeasons() {
		let e = J(this._seasons ?? []);
		this._chosen = this._chosen.size === e.length ? /* @__PURE__ */ new Set() : new Set(e);
	}
	async _request() {
		let e = this._selected;
		if (!e || this._requesting) return;
		let t = {
			type: `${Z}/request`,
			tmdb_id: e.tmdb_id,
			media_type: e.media_type,
			is_4k: this._is4k,
			...this._entry()
		};
		e.media_type === "tv" && (t.seasons = this._seasons ? [...this._chosen].sort((e, t) => e - t) : "all"), this._requesting = !0;
		try {
			await this.hass.callWS(t), W(this, `Requested ${e.title}`), this._markRequested(e);
		} catch (e) {
			W(this, `Request failed: ${G(e)}`);
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
					type: `${Z}/remove`,
					tmdb_id: e.tmdb_id,
					media_type: e.media_type,
					...this._entry()
				}), W(this, `Removed ${e.title}`), this._setStatus(e, "deleted");
			} catch (e) {
				W(this, `Remove failed: ${G(e)}`);
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
				type: `${Z}/episodes`,
				tmdb_id: e,
				season_number: t,
				...this._entry()
			});
			if (r.added && (this._addedSeries = r.series_id), !n()) return;
			this._episodes = r;
		} catch (e) {
			n() && (this._episodesError = G(e));
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
			type: `${Z}/episodes/discard`,
			series_id: e,
			...this._entry()
		}).catch(() => void 0);
	}
	_back() {
		this._leaveShow(), this._closeEpisodes(), this._selected = void 0;
	}
	_togglePick(e) {
		let t = new Set(this._picked);
		t.has(e) ? t.delete(e) : t.add(e), this._picked = t;
	}
	_toggleAllPicks() {
		let e = De(this._episodes?.episodes ?? []);
		this._picked = this._picked.size === e.length ? /* @__PURE__ */ new Set() : new Set(e);
	}
	async _download() {
		let e = this._episodes;
		if (!e || !this._picked.size || this._pickerBusy || !this._selected) return;
		let t = [...this._picked];
		this._pickerBusy = !0;
		try {
			await this.hass.callWS({
				type: `${Z}/episodes/download`,
				series_id: e.series_id,
				episode_ids: t,
				...this._entry()
			}), this._addedSeries = void 0, W(this, `Downloading ${t.length} episode${t.length === 1 ? "" : "s"} of ${e.title}`), this._picked = /* @__PURE__ */ new Set();
			let n = this._selected.tmdb_id;
			await this._loadEpisodes(n, e.season_number), this._clearRefreshTimers(), this._refreshTimers = Ne.map((t) => setTimeout(() => {
				this._episodes?.series_id === e.series_id && this._loadEpisodes(n, e.season_number);
			}, t));
		} catch (e) {
			W(this, `Download failed: ${G(e)}`);
		} finally {
			this._pickerBusy = !1;
		}
	}
	_askRemoveEpisode(e, t) {
		t.preventDefault(), t.stopPropagation(), this._confirmRemoveEp = e;
	}
	async _removeEpisode(e) {
		let t = this._episodes;
		if (t && !this._pickerBusy && this._selected) {
			this._pickerBusy = !0;
			try {
				let n = await this.hass.callWS({
					type: `${Z}/episodes/remove`,
					series_id: t.series_id,
					episode_ids: [e.id],
					...this._entry()
				});
				this._confirmRemoveEp = void 0, n.show_removed ? (W(this, `Removed episode ${e.episode_number}. Nothing else was left, so ${t.title} is out of Sonarr too.`), this._addedSeries = void 0, this._closeEpisodes()) : (W(this, `Removed episode ${e.episode_number} of ${t.title}`), await this._loadEpisodes(this._selected.tmdb_id, t.season_number));
			} catch (e) {
				W(this, `Remove failed: ${G(e)}`);
			} finally {
				this._pickerBusy = !1;
			}
		}
	}
	async _setOption(e, t) {
		let n = this._episodes;
		if (n && !this._pickerBusy && this._selected) {
			this._pickerBusy = !0;
			try {
				(await this.hass.callWS({
					type: `${Z}/episodes/options`,
					series_id: n.series_id,
					[e]: t,
					...this._entry()
				})).follow_new && (this._addedSeries = void 0), await this._loadEpisodes(this._selected.tmdb_id, n.season_number);
			} catch (e) {
				W(this, `Couldn't change it: ${G(e)}`);
			} finally {
				this._pickerBusy = !1;
			}
		}
	}
	render() {
		return this._config ? M`
      <ha-card .header=${this._config.title || void 0}>
        ${this._staleVersion ? M`<div class="stale">
              Card is out of date (server has ${this._staleVersion}).
              <button class="link" @click=${this._reload}>Reload</button>
            </div>` : P}
        ${this._selected && this._episodeSeason ? this._renderEpisodes(this._selected, this._episodeSeason) : this._selected ? this._renderDetail(this._selected) : this._renderSearch()}
      </ha-card>
    ` : P;
	}
	_renderSearch() {
		return M`
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
          ${this._query ? M`<button class="icon" aria-label="Clear" @click=${this._clear}>
                <ha-icon icon="mdi:close"></ha-icon>
              </button>` : P}
        </div>
        <div class="chips" role="radiogroup" aria-label="Media type">
          ${Fe.map((e) => M`<button
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
		return this._showBrowse() ? this._renderBrowse() : this._error ? M`<div class="message error">${this._error}</div>` : this._loading && !this._results ? M`<div class="message">Searching…</div>` : this._results ? this._results.length ? M`
      <div class="grid ${this._loading ? "busy" : ""}">
        ${this._results.map((e) => this._renderTile(e))}
      </div>
    ` : M`<div class="message">No movies or shows found.</div>` : P;
	}
	_renderBrowse() {
		let e = Ie.find((e) => e.value === this._browse).heading, t;
		return t = this._browseError ? M`<div class="message error">Couldn't load ${e.toLowerCase()} (${this._browseError}).</div>` : this._browseResults ? this._browseResults.length ? M`<div class="grid">${this._browseResults.map((e) => this._renderTile(e))}</div>` : M`<div class="message">Nothing to show.</div>` : M`<div class="message">Loading…</div>`, M`
      <div class="section">
        <span>${e}</span>
        <div class="chips small" role="radiogroup" aria-label="Browse">
          ${Ie.map((e) => M`<button
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
	_renderTile(e) {
		let t = q(e.status);
		return M`
      <button class="tile" @click=${() => this._open(e)} aria-label="${e.title} ${e.year ?? ""}">
        <div class="poster">
          ${e.poster_url ? M`<img src=${e.poster_url} alt="" loading="lazy" />` : M`<ha-icon icon=${e.media_type === "tv" ? "mdi:television-classic" : "mdi:movie-open"}></ha-icon>`}
          ${t ? M`<span class="status ${e.status}">${t}</span>` : P}
          <span class="kind">${e.media_type === "tv" ? "TV" : "Movie"}</span>
        </div>
        <div class="title">${e.title}</div>
        <div class="year">${e.year ?? ""}</div>
      </button>
    `;
	}
	_renderDetail(e) {
		let t = q(e.status), n = e.media_type === "tv", r = n ? Te(e.status) && (!this._seasons || this._chosen.size > 0) : K(e.status);
		return M`
      <div class="detail">
        <button class="back" @click=${this._back}>
          <ha-icon icon="mdi:arrow-left"></ha-icon> Back
        </button>
        <div class="head">
          ${e.poster_url ? M`<img class="thumb" src=${e.poster_url} alt="" />` : P}
          <div>
            <h2>${e.title}</h2>
            <div class="meta">
              ${e.year ?? ""} · ${n ? "TV show" : "Movie"}
              ${t ? M`<span class="status inline ${e.status}">${t}</span>` : P}
            </div>
          </div>
        </div>
        ${e.overview ? M`<p class="overview">${e.overview}</p>` : P}
        ${n ? this._renderSeasons() : P}
        ${this._config.show_4k && r ? M`<label class="row">
              <input type="checkbox" .checked=${this._is4k} @change=${(e) => this._is4k = e.target.checked} />
              Request in 4K
            </label>` : P}
        <button class="primary" ?disabled=${!r || this._requesting} @click=${this._request}>
          ${this._requesting ? "Requesting…" : r ? "Request" : t ?? "Unavailable"}
        </button>
        ${this._config.show_remove && we(e.status) ? this._renderRemove(e) : P}
      </div>
    `;
	}
	_renderRemove(e) {
		let t = e.media_type === "tv" ? "the whole show" : "this movie";
		return this._confirmRemove ? M`
      <div class="confirm" role="alert">
        Delete ${t} and its files from ${e.media_type === "tv" ? "Sonarr" : "Radarr"}? This can't be
        undone.
      </div>
      <div class="confirm-row">
        <button class="secondary" ?disabled=${this._removing} @click=${() => this._confirmRemove = !1}>
          Cancel
        </button>
        <button class="danger solid" ?disabled=${this._removing} @click=${this._remove}>
          ${this._removing ? "Removing…" : "Delete files"}
        </button>
      </div>
    ` : M`<button class="danger" @click=${this._remove}>Remove…</button>`;
	}
	_renderSeasons() {
		if (this._seasonsError) return M`<div class="message error">Couldn't load seasons (${this._seasonsError}). Request will ask for all.</div>`;
		if (!this._seasons) return M`<div class="message">Loading seasons…</div>`;
		let e = J(this._seasons);
		return M`
      <div class="seasons">
        <div class="seasons-head">
          <span>Seasons</span>
          ${e.length > 1 ? M`<button class="link" @click=${this._toggleAllSeasons}>
                ${this._chosen.size === e.length ? "Select none" : "Select all"}
              </button>` : P}
        </div>
        ${this._seasons.map((e) => {
			let t = K(e.status), n = q(e.status);
			return M`<label class="row season ${t ? "" : "done"}">
            <input
              type="checkbox"
              .checked=${!t || this._chosen.has(e.season_number)}
              ?disabled=${!t}
              @change=${() => this._toggleSeason(e.season_number)}
            />
            <span class="grow">${e.name}</span>
            ${n ? M`<span class="status inline ${e.status}">${n}</span>` : P}
            ${this._picker ? M`<button class="link episodes-link" @click=${(t) => this._openEpisodes(e, t)}>
                  Episodes
                </button>` : P}
          </label>`;
		})}
      </div>
    `;
	}
	_renderEpisodes(e, t) {
		let n = this._episodes, r;
		if (this._episodesError) r = M`<div class="message error">Couldn't load episodes (${this._episodesError}).</div>`;
		else if (!n) r = M`<div class="message">Loading episodes from Sonarr…</div>`;
		else {
			let e = De(n.episodes), t = this._picked.size;
			r = M`
        <div class="seasons options">
          <label class="row option">
            <input
              type="checkbox"
              .checked=${n.follow_new}
              ?disabled=${this._pickerBusy}
              @change=${(e) => this._setOption("follow_new", e.target.checked)}
            />
            <span class="grow">
              Get new episodes
              <span class="hint">
                Download future episodes of ${n.title} when they air. Turning it off also cancels
                upcoming episodes you picked.
              </span>
            </span>
          </label>
          <label class="row option">
            <input
              type="checkbox"
              .checked=${n.daily}
              ?disabled=${this._pickerBusy}
              @change=${(e) => this._setOption("daily", e.target.checked)}
            />
            <span class="grow">
              Daily show
              <span class="hint">
                For shows released by date, like quizzes and soaps. Turning it on searches again for
                wanted episodes.
              </span>
            </span>
          </label>
        </div>
        <div class="seasons">
          <div class="seasons-head">
            <span>${n.episodes.length} episodes</span>
            ${e.length > 1 ? M`<button class="link" @click=${this._toggleAllPicks}>
                  ${t === e.length ? "Select none" : `Select all ${e.length}`}
                </button>` : P}
          </div>
          ${n.episodes.length ? n.episodes.map((e) => {
				let t = Ee(e), n = Oe(e);
				return M`<label class="row season episode ${t ? "" : "done"}">
                  <input
                    type="checkbox"
                    .checked=${t ? this._picked.has(e.id) : e.status !== "not_aired" || e.monitored}
                    ?disabled=${!t}
                    @change=${() => this._togglePick(e.id)}
                  />
                  <span class="grow">
                    <span class="ep-title">${e.episode_number}. ${e.title || `Episode ${e.episode_number}`}</span>
                    <span class="hint">${ke(e.air_date)}</span>
                  </span>
                  ${n ? M`<span class="status inline ep ${e.status}">${n}</span>` : P}
                  ${this._config.show_remove && e.status === "downloaded" && this._confirmRemoveEp !== e.id ? M`<button class="link ep-remove" @click=${(t) => this._askRemoveEpisode(e.id, t)}>
                        Remove
                      </button>` : P}
                </label>
                ${this._confirmRemoveEp === e.id ? M`<div class="ep-confirm" role="alert">
                      <span class="grow">Delete episode ${e.episode_number}'s file? This can't be undone.</span>
                      <button class="secondary small" ?disabled=${this._pickerBusy} @click=${() => this._confirmRemoveEp = void 0}>
                        Cancel
                      </button>
                      <button class="danger solid small" ?disabled=${this._pickerBusy} @click=${() => this._removeEpisode(e)}>
                        ${this._pickerBusy ? "Deleting…" : "Delete file"}
                      </button>
                    </div>` : P}`;
			}) : M`<div class="message">Sonarr lists no episodes for this season yet.</div>`}
        </div>
        ${t > 20 ? M`<div class="warn">That's ${t} episodes. Check there's room before downloading.</div>` : P}
        <button class="primary" ?disabled=${!t || this._pickerBusy} @click=${this._download}>
          ${this._pickerBusy ? "Working…" : t ? `Download ${t} episode${t === 1 ? "" : "s"}` : "Pick episodes to download"}
        </button>
      `;
		}
		return M`
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
X = $, X.properties = {
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
	_confirmRemoveEp: { state: !0 }
}, X.styles = o`
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
export { Ae as CARD_VERSION, $ as JellyseerrSearchCard };
