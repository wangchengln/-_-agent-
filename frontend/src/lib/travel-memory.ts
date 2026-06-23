import { readFile, saveFile } from "@/lib/api";
import type { PreferenceProfile } from "@/lib/recommend-types";
import { formatPreferenceForMemory } from "@/lib/weekend-bridge";

const USER_MD_PATH = "workspace/USER.md";
const SECTION_HEADER = "## 周末出行偏好";

export async function syncTravelPreferencesToMemory(
  preference: PreferenceProfile,
  lastCommand: string
): Promise<boolean> {
  const snippet = formatPreferenceForMemory(preference, lastCommand);
  const block = `${SECTION_HEADER}\n${snippet}\n`;

  let content: string;
  try {
    content = await readFile(USER_MD_PATH);
  } catch {
    content = "# USER — 用户画像\n\n";
  }

  const sectionRegex = new RegExp(
    `${SECTION_HEADER.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}[\\s\\S]*?(?=\\n## |$)`
  );

  const updated = sectionRegex.test(content)
    ? content.replace(sectionRegex, `${block.trim()}\n`)
    : `${content.trim()}\n\n${block}`;

  await saveFile(USER_MD_PATH, updated.endsWith("\n") ? updated : `${updated}\n`);
  return true;
}
