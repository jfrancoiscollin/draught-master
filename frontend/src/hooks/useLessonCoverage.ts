/**
 * Lesson coverage prefetch.
 *
 * Returns the set of motif slugs and weakness families that have at
 * least one chapter in `manuel_debutant.md` covering them, alongside
 * a resolver that opens the first matching chapter via `onOpenLesson`.
 *
 * Consumers gate their "📖 leçon" badges on `coverage.motifs.has(slug)`
 * (resp. `coverage.weaknesses.has(family)`) so we never render a
 * dead button. The coverage fetch is unauthenticated and lightweight
 * (16 chapters × {title, motifs, weaknesses}); failures degrade to
 * "no badges" silently.
 */
import { useEffect, useState } from 'react'
import { getLessonTitles, getLessonsByMotif, getLessonsByWeakness } from '../api/client'

export interface LessonCoverage {
  motifs: Set<string>
  weaknesses: Set<string>
}

export interface UseLessonCoverage {
  coverage: LessonCoverage
  /** Look up the first matching chapter for a motif and forward to
   *  `onOpenLesson`. No-op when `onOpenLesson` is undefined or no
   *  chapter matches (guard with `coverage.motifs.has(slug)` to keep
   *  the click reliable). */
  openLessonForMotif: (slug: string) => void
  openLessonForWeakness: (family: string) => void
}

export function useLessonCoverage(
  onOpenLesson: ((chapter: number) => void) | undefined,
): UseLessonCoverage {
  const [coverage, setCoverage] = useState<LessonCoverage>({
    motifs: new Set(),
    weaknesses: new Set(),
  })

  useEffect(() => {
    let cancelled = false
    getLessonTitles().then(table => {
      if (cancelled) return
      const motifs = new Set<string>()
      const weaknesses = new Set<string>()
      for (const ch of Object.values(table)) {
        const m = (ch as { motifs?: string[] }).motifs ?? []
        const w = (ch as { weaknesses?: string[] }).weaknesses ?? []
        m.forEach(s => motifs.add(s))
        w.forEach(s => weaknesses.add(s))
      }
      setCoverage({ motifs, weaknesses })
    }).catch(() => { /* no badges — acceptable degradation */ })
    return () => { cancelled = true }
  }, [])

  const openLessonForMotif = (slug: string) => {
    if (!onOpenLesson) return
    getLessonsByMotif(slug).then(matches => {
      if (matches[0]) onOpenLesson(matches[0].chapter)
    })
  }
  const openLessonForWeakness = (family: string) => {
    if (!onOpenLesson) return
    getLessonsByWeakness(family).then(matches => {
      if (matches[0]) onOpenLesson(matches[0].chapter)
    })
  }

  return { coverage, openLessonForMotif, openLessonForWeakness }
}
