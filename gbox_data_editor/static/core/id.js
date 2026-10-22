/**
 * id.js — Global unique ID generation (int64: 48-bit timestamp + 16-bit random).
 */

export function genId() {
    const ts = BigInt(Date.now()) & 0xFFFFFFFFFFFFn;
    const rand = BigInt(Math.floor(Math.random() * 0x10000));
    return Number((ts << 16n) | rand);
}
