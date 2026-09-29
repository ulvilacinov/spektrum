// Only what the tests use from Node; the app's types stay browser-only (no @types/node).
declare module 'node:buffer' {
  export const File: typeof globalThis.File
}
