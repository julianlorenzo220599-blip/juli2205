const crypto = require('crypto');

function parseAuthHeader(header) {
  if (typeof header !== 'string') return null;
  const match = header.match(/^Bearer\s+(.+)$/i);
  if (!match) return null;
  const token = match[1].trim();
  return token.length > 0 ? token : null;
}

function isValidToken(token, expected) {
  if (typeof token !== 'string' || typeof expected !== 'string') return false;
  if (token.length !== expected.length) return false;
  const a = Buffer.from(token);
  const b = Buffer.from(expected);
  return crypto.timingSafeEqual(a, b);
}

function authenticate(req, expected) {
  if (!expected) return false;
  const header = req && req.headers && req.headers.authorization;
  const token = parseAuthHeader(header);
  if (!token) return false;
  return isValidToken(token, expected);
}

module.exports = { parseAuthHeader, isValidToken, authenticate };
