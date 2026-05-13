import { defineCloudflareConfig } from '@opennextjs/cloudflare';

// OpenNext adapter config for Cloudflare Workers.
// Docs: https://opennext.js.org/cloudflare/get-started
//
// Year-1 stance:
// - No incremental cache yet. Pulse + Verdict will revalidate via on-demand
//   revalidation once we have data — Day 4–6+ work. Add a KV-backed cache then.
// - No queue / tag-cache / R2 cache yet (R2 deferred per ADR-0004).
export default defineCloudflareConfig();
