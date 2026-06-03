#!/usr/bin/env node

const API_BASE = process.env.CRM_API_BASE || "https://btc.mechanicalpeexamprep.com/api/crm";
const API_KEY = process.env.CRM_API_KEY;
const APPLY = process.argv.includes("--apply");
const INTERNAL_DOMAIN_RE = /(?:^|\.)mechanicalpeexamprep\.com$/i;

if (!API_KEY) {
  console.error("Missing CRM_API_KEY. Example:");
  console.error("  $env:CRM_API_KEY='...'; node scripts/crm-email-contact-repair.js --apply");
  process.exit(1);
}

async function api(method, path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${API_KEY}`,
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  const payload = text ? JSON.parse(text) : null;
  if (!res.ok) {
    throw new Error(`${method} ${path} failed: ${payload?.error || res.statusText}`);
  }
  return payload;
}

function titleCaseName(value) {
  return String(value || "")
    .replace(/[_\-.]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function emailDomain(email) {
  const at = String(email || "").lastIndexOf("@");
  return at === -1 ? "" : email.slice(at + 1).toLowerCase();
}

function isInternalEmail(email) {
  return INTERNAL_DOMAIN_RE.test(emailDomain(email));
}

function cleanEmail(value) {
  const match = String(value || "").match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,24}/i);
  if (!match) return null;
  let email = match[0].replace(/[)\].,;:]+$/, "");
  if (/\.comm$/i.test(email)) email = email.slice(0, -1);
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return null;
  return email;
}

function looksLikeEmail(value) {
  return /@/.test(String(value || ""));
}

function parseFormFields(raw) {
  const text = String(raw || "").replace(/\r\n/g, "\n");
  const match = text.match(/(?:^|\n)\s*Name\s*\n\s*([^\n]+?)\s*\n\s*Email\s*\n\s*([^\n\s]+@[^\n\s]+)\s*(?:\n|$)/i);
  if (!match) return null;
  const name = match[1].trim();
  const email = cleanEmail(match[2]);
  if (!name || !email || isInternalEmail(email)) return null;
  return { name, email, reason: "explicit Name/Email fields" };
}

function parseAngleSender(raw) {
  const text = String(raw || "").replace(/\r\n/g, "\n");
  const re = /(^|\n|On\s+[^\n]*?\s)([^<>\n]{2,80})\s*<([^<>\s]+@[^<>\s]+)>/gi;
  let match;
  while ((match = re.exec(text))) {
    const name = match[2].replace(/^wrote:\s*/i, "").trim();
    const email = cleanEmail(match[3]);
    if (!name || !email || isInternalEmail(email)) continue;
    if (/mechanical pe exam prep|dan molloy/i.test(name)) continue;
    return { name, email, reason: "external sender header" };
  }
  return null;
}

function parseVisibleSender(raw) {
  const lines = String(raw || "")
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const first = lines[0] || "";
  if (!first || looksLikeEmail(first) || /^on\s+/i.test(first)) return null;
  if (/mechanical pe exam prep|dan molloy/i.test(first)) return null;

  for (const line of lines) {
    const email = cleanEmail(line);
    if (email && !isInternalEmail(email)) {
      return { name: first, email, reason: "visible sender plus external email" };
    }
  }
  return null;
}

function deriveFromEmail(email) {
  if (!email || isInternalEmail(email)) return null;
  const local = email.split("@")[0];
  const name = titleCaseName(local.replace(/\d+$/g, ""));
  if (!name || name.length < 2) return null;
  return { name, email, reason: "derived from email local part" };
}

function inferContactFix(contact) {
  const raw = contact.interactions?.[contact.interactions.length - 1]?.raw_content
    || contact.interactions?.[0]?.raw_content
    || contact.notes
    || "";

  const currentNameBad = looksLikeEmail(contact.name) || !contact.name || contact.name === "(unknown)";
  const currentEmailBad = !cleanEmail(contact.email) || isInternalEmail(contact.email);
  if (!currentNameBad && !currentEmailBad) return null;

  const inferred =
    parseFormFields(raw)
    || parseAngleSender(raw)
    || parseVisibleSender(raw)
    || deriveFromEmail(cleanEmail(contact.email));

  if (!inferred) return null;

  const payload = {};
  if (currentNameBad && inferred.name && inferred.name !== contact.name) payload.name = inferred.name;
  if ((currentEmailBad || inferred.email !== contact.email) && inferred.email) payload.email = inferred.email;
  if (!Object.keys(payload).length) return null;

  return { id: contact.id, before: { name: contact.name, email: contact.email }, payload, reason: inferred.reason };
}

async function main() {
  const contacts = await api("GET", "/contacts");
  const emailContacts = contacts.filter((c) => c.source === "Email");
  const fixes = [];

  for (const row of emailContacts) {
    if (!looksLikeEmail(row.name) && cleanEmail(row.email) && !isInternalEmail(row.email)) continue;
    const contact = await api("GET", `/contacts/${row.id}`);
    const fix = inferContactFix(contact);
    if (fix) fixes.push(fix);
  }

  if (!fixes.length) {
    console.log("No Email-sourced contact identity anomalies found.");
    return;
  }

  for (const fix of fixes) {
    console.log(`${APPLY ? "Applying" : "Would apply"} contact ${fix.id}: ${fix.reason}`);
    console.log(`  before: ${fix.before.name} <${fix.before.email || ""}>`);
    console.log(`  after:  ${fix.payload.name || fix.before.name} <${fix.payload.email || fix.before.email || ""}>`);
    if (APPLY) await api("PUT", `/contacts/${fix.id}`, fix.payload);
  }

  if (!APPLY) {
    console.log("\nDry run only. Re-run with --apply to write these high-confidence fixes.");
  }
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
