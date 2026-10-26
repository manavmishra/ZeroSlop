export type HygieneEdit = { start: number; end: number; original: string; replacement: ''; reason: string; outputStart: number; outputBinding: string };
export type HygieneResult = { text: string; edits: HygieneEdit[]; status: 'cleaned' | 'unchanged'; policyVersion: string; offsetUnit: 'utf16'; statisticalWatermark: { status: 'not_verified'; reason: string } };
export function cleanTextHygiene(text: string): HygieneResult;
export function inspectTextHygiene(text: string): Omit<HygieneResult, 'status'> & { status: 'inspected'; findings: Array<{ start: number; codePoint: string; disposition: 'removable' | 'preserved' }> };
export function reverseTextHygiene(text: string, edits: HygieneEdit[]): string;
export function createTextHygiene(): { cleanTextHygiene: typeof cleanTextHygiene; inspectTextHygiene: typeof inspectTextHygiene; reverseTextHygiene: typeof reverseTextHygiene };
