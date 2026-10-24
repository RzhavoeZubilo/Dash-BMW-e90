// Телеграммы BMW-FAST для кабеля K+DCAN в режиме D-CAN.
// Кабель сам делает ISO-TP по CAN; хост шлёт по COM-порту (115200 8N1) ту же
// телеграмму, что и на K-линии: [0x80|len] [TGT] [SRC] [data…] [sum8].
// Источник формата: docs/D-CAN_TRANSPORT_RESEARCH.md §1.2.
(function (root) {
  'use strict';

  var TESTER = 0xF1;

  function sum8(bytes, end) {
    var s = 0;
    for (var i = 0; i < end; i++) s = (s + bytes[i]) & 0xFF;
    return s;
  }

  function buildTelegram(target, data) {
    var out;
    if (data.length <= 0x3F) {
      out = [0x80 | data.length, target, TESTER].concat(data);
    } else if (data.length < 0x100) {
      out = [0x80, target, TESTER, data.length].concat(data);
    } else {
      throw new Error('payload too long');
    }
    out.push(sum8(out, out.length));
    return out;
  }

  // Ищет первую полную телеграмму в buf. Возвращает
  // { need } — данных пока мало; { error } — мусор/сумма не сошлась;
  // { tel: {target, source, data, raw}, size } — готово.
  function parseTelegram(buf) {
    if (buf.length < 4) return { need: true };
    var fmt = buf[0];
    if ((fmt & 0xC0) !== 0x80) return { error: 'bad format byte 0x' + hex(fmt) };
    var len = fmt & 0x3F, start = 3;
    if (len === 0) { len = buf[3]; start = 4; }
    var size = start + len + 1;
    if (buf.length < size) return { need: true };
    if (sum8(buf, size - 1) !== buf[size - 1]) return { error: 'checksum mismatch' };
    return {
      size: size,
      tel: { target: buf[1], source: buf[2], data: buf.slice(start, start + len), raw: buf.slice(0, size) }
    };
  }

  function hex(b) { return (b < 16 ? '0' : '') + b.toString(16).toUpperCase(); }
  function hexStr(bytes) { return Array.prototype.map.call(bytes, hex).join(' '); }
  function bcd(bytes) { return Array.prototype.map.call(bytes, hex).join(''); }

  // Разбор ответа IDENT ($1A $80) — смещения и преобразования взяты из байткода
  // джоба IDENT в KOMB87.prg (SP-Daten 69). Отсчёт от байта сервиса 0x5A.
  function decodeIdent(d) {
    if (d[0] === 0x7F) return { negative: true, service: d[1], nrc: d[2] };
    if (d[0] !== 0x5A || d[1] !== 0x80) return { unexpected: true };
    var r = {};
    function has(n) { return d.length > n; }
    if (has(7)) {
      var nr = d.slice(2, 8);
      r.ID_BMW_NR = nr[0] === 0
        ? bcd(nr).slice(5)
        : String.fromCharCode(nr[0], nr[1], nr[2]) + bcd(nr.slice(3));
    }
    if (has(8)) r.ID_HW_NR = hex(d[8]);
    if (has(9)) r.ID_COD_INDEX = d[9];
    if (has(11)) r.ID_DIAG_INDEX = (d[10] << 8) + d[11];
    if (has(13)) r.ID_VAR_INDEX = (d[12] << 8) + d[13];
    if (has(17)) r.ID_DATUM = bcd([d[17]]) + '.' + bcd([d[16]]) + '.' + bcd(d.slice(14, 16));
    if (has(18)) r.ID_LIEF_NR = bcd([d[18]]);
    var sw = ['ID_SW_NR_MCV', 'ID_SW_NR_FSV', 'ID_SW_NR_OSV', 'ID_SW_NR_RES'];
    for (var i = 0; i < sw.length; i++) {
      var o = 0x13 + i * 3;
      if (has(o + 2)) r[sw[i]] = d[o] + '.' + d[o + 1] + '.' + d[o + 2];
    }
    return r;
  }

  var api = { buildTelegram: buildTelegram, parseTelegram: parseTelegram, decodeIdent: decodeIdent,
              hexStr: hexStr, sum8: sum8, TESTER: TESTER };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.BmwFast = api;
})(this);
