const { test } = require('node:test');
const assert = require('node:assert/strict');
const { parseAuthHeader, isValidToken, authenticate } = require('./auth');

test('parseAuthHeader extrae token de un Bearer válido', () => {
  assert.equal(parseAuthHeader('Bearer abc123'), 'abc123');
});

test('parseAuthHeader es case-insensitive sobre el esquema', () => {
  assert.equal(parseAuthHeader('bearer xyz'), 'xyz');
  assert.equal(parseAuthHeader('BEARER xyz'), 'xyz');
});

test('parseAuthHeader devuelve null si falta el esquema', () => {
  assert.equal(parseAuthHeader('abc123'), null);
  assert.equal(parseAuthHeader('Basic abc123'), null);
});

test('parseAuthHeader devuelve null para entradas no string', () => {
  assert.equal(parseAuthHeader(undefined), null);
  assert.equal(parseAuthHeader(null), null);
  assert.equal(parseAuthHeader(42), null);
});

test('parseAuthHeader devuelve null si el token está vacío', () => {
  assert.equal(parseAuthHeader('Bearer    '), null);
});

test('isValidToken acepta tokens idénticos', () => {
  assert.equal(isValidToken('sk-test-123', 'sk-test-123'), true);
});

test('isValidToken rechaza tokens distintos de igual largo', () => {
  assert.equal(isValidToken('sk-test-aaa', 'sk-test-bbb'), false);
});

test('isValidToken rechaza tokens de distinto largo sin tirar', () => {
  assert.equal(isValidToken('corto', 'token-largo'), false);
});

test('isValidToken rechaza entradas no string', () => {
  assert.equal(isValidToken(null, 'x'), false);
  assert.equal(isValidToken('x', undefined), false);
});

test('authenticate valida un request con header Bearer correcto', () => {
  const req = { headers: { authorization: 'Bearer secreto-rv-2026' } };
  assert.equal(authenticate(req, 'secreto-rv-2026'), true);
});

test('authenticate rechaza un request sin header authorization', () => {
  assert.equal(authenticate({ headers: {} }, 'secreto-rv-2026'), false);
});

test('authenticate rechaza un request con token incorrecto', () => {
  const req = { headers: { authorization: 'Bearer otro-token' } };
  assert.equal(authenticate(req, 'secreto-rv-2026'), false);
});

test('authenticate falla cerrado si no hay token esperado configurado', () => {
  const req = { headers: { authorization: 'Bearer lo-que-sea' } };
  assert.equal(authenticate(req, ''), false);
  assert.equal(authenticate(req, undefined), false);
});

test('authenticate tolera requests malformados sin tirar', () => {
  assert.equal(authenticate(null, 'x'), false);
  assert.equal(authenticate({}, 'x'), false);
  assert.equal(authenticate({ headers: null }, 'x'), false);
});
