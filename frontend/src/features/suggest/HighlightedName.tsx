import type { NameSegment } from "../../api/client";

/**
 * The display name with the parts matching the query in bold.
 * The backend already cut it ("mime" -> "Mr. " + **"Mime"**): concatenating
 * the segments always gives the full name.
 */
export function HighlightedName({ segments }: { segments: NameSegment[] }) {
  let offset = 0;
  return (
    <span>
      {segments.map((segment) => {
        const key = offset;
        offset += segment.text.length;
        return segment.matched ? (
          <strong key={key} className="font-bold text-red-600">
            {segment.text}
          </strong>
        ) : (
          <span key={key}>{segment.text}</span>
        );
      })}
    </span>
  );
}
