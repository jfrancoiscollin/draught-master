import React, { useEffect, useState } from 'react'
import { useLanguage } from '../i18n/LanguageContext'
import { useAuth } from '../contexts/AuthContext'
import { getLessonTitles, getExercises, getReadLessons, getUserProgress } from '../api/client'

interface Book {
  id: string
  title: string
  titleEn: string
  author: string
  category: 'manuel'
  emoji: string
  hasExercises: boolean
}

// Manuels pédagogiques préprocessés par Claude via dilf (un par niveau).
// Voir `dilf/docs/MANUELS_PIPELINE.md` et `backend/manuels/`.
const BOOKS: Book[] = [
  {
    id: 'manuel_debutant',
    title: 'Manuel Débutant',
    titleEn: 'Beginner Manual',
    author: 'Draught Master',
    category: 'manuel',
    emoji: '🌱',
    hasExercises: true,
  },
  {
    id: 'manuel_intermediaire',
    title: 'Manuel Intermédiaire',
    titleEn: 'Intermediate Manual',
    author: 'Draught Master',
    category: 'manuel',
    emoji: '🌿',
    hasExercises: false,
  },
  {
    id: 'manuel_avance',
    title: 'Manuel Avancé',
    titleEn: 'Advanced Manual',
    author: 'Draught Master',
    category: 'manuel',
    emoji: '🌳',
    hasExercises: false,
  },
  {
    id: 'manuel_expert',
    title: 'Manuel Expert',
    titleEn: 'Expert Manual',
    author: 'Draught Master',
    category: 'manuel',
    emoji: '🏆',
    hasExercises: false,
  },
]

const CATEGORY_LABELS: Record<string, Record<'fr' | 'en', string>> = {
  manuel: { fr: 'Manuels pédagogiques', en: 'Pedagogical manuals' },
}

interface BookStats {
  totalLessons: number
  totalExercises: number
  readLessons: number
  solvedExercises: number
}

function ProgressBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-500 ${color}`}
        style={{ width: `${Math.min(100, value)}%` }}
      />
    </div>
  )
}

interface ExerciseLibraryPageProps {
  onSelectBook: (bookId: string) => void
}

export default function ExerciseLibraryPage({ onSelectBook }: ExerciseLibraryPageProps) {
  const { t, language } = useLanguage()
  const { user } = useAuth()
  const [stats, setStats] = useState<Record<string, BookStats>>({})

  const enabledBooks = BOOKS.filter(b => b.hasExercises)

  useEffect(() => {
    // Fetch totals for each enabled book
    Promise.all(
      enabledBooks.map(book =>
        Promise.all([
          getLessonTitles(book.id),
          getExercises({ book_id: book.id }),
        ]).then(([lessons, exercises]) => ({
          bookId: book.id,
          totalLessons: Object.keys(lessons).length,
          totalExercises: exercises.length,
          exerciseIds: exercises.map(e => e.id),
        }))
      )
    ).then(results => {
      setStats(prev => {
        const next = { ...prev }
        for (const r of results) {
          next[r.bookId] = {
            totalLessons: r.totalLessons,
            totalExercises: r.totalExercises,
            readLessons: prev[r.bookId]?.readLessons ?? 0,
            solvedExercises: prev[r.bookId]?.solvedExercises ?? 0,
          }
        }
        return next
      })
    }).catch(() => {})
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!user) {
      setStats(prev => {
        const next = { ...prev }
        for (const book of enabledBooks) {
          if (next[book.id]) {
            next[book.id] = { ...next[book.id], readLessons: 0, solvedExercises: 0 }
          }
        }
        return next
      })
      return
    }
    // Fetch user progress alongside per-book exercise lists to count solved per book
    Promise.all([
      getReadLessons(),
      getUserProgress(),
      ...enabledBooks.map(book => getExercises({ book_id: book.id })),
    ]).then(([readChapters, solvedIds, ...bookExerciseLists]) => {
      const solvedSet = new Set(solvedIds as number[])
      setStats(prev => {
        const next = { ...prev }
        enabledBooks.forEach((book, i) => {
          const bookExIds = (bookExerciseLists[i] as { id: number }[]).map(e => e.id)
          // Count how many of this book's chapter numbers appear in readChapters
          const bookChapters = (bookExerciseLists[i] as { chapter?: number }[])
            .map(e => e.chapter)
            .filter((c): c is number => c != null)
          const uniqueChapters = new Set(bookChapters)
          const readCount = (readChapters as number[]).filter(ch => uniqueChapters.has(ch)).length
          next[book.id] = {
            totalLessons: prev[book.id]?.totalLessons ?? 0,
            totalExercises: prev[book.id]?.totalExercises ?? 0,
            readLessons: readCount,
            solvedExercises: bookExIds.filter(id => solvedSet.has(id)).length,
          }
        })
        return next
      })
    }).catch(() => {})
  }, [user]) // eslint-disable-line react-hooks/exhaustive-deps

  const categories: Book['category'][] = ['manuel']

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <h2 className="text-xl font-bold text-amber-500 mb-1">{t('tabExercises')}</h2>
        <p className="text-gray-400 text-sm mb-8">{t('chooseBook')}</p>

        {categories.map(cat => {
          const books = BOOKS.filter(b => b.category === cat)
          return (
            <div key={cat} className="mb-8">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3 border-b border-gray-700 pb-1">
                {CATEGORY_LABELS[cat][language]}
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {books.map(book => {
                  const s = stats[book.id]
                  const lessonPct = s && s.totalLessons > 0 ? Math.round((s.readLessons / s.totalLessons) * 100) : 0
                  const exercisePct = s && s.totalExercises > 0 ? Math.round((s.solvedExercises / s.totalExercises) * 100) : 0

                  return (
                    <button
                      key={book.id}
                      onClick={() => book.hasExercises && onSelectBook(book.id)}
                      disabled={!book.hasExercises}
                      className={`group relative flex flex-col items-start gap-2 rounded-xl border p-5 text-left transition-all duration-200 ${
                        book.hasExercises
                          ? 'bg-gray-800 border-gray-700 hover:border-amber-600 hover:bg-gray-750 cursor-pointer'
                          : 'bg-gray-850 border-gray-800 opacity-60 cursor-not-allowed'
                      }`}
                    >
                      {!book.hasExercises && (
                        <span className="absolute top-3 right-3 text-xs bg-gray-700 text-gray-400 px-2 py-0.5 rounded-full">
                          {t('comingSoon')}
                        </span>
                      )}
                      <span className="text-3xl">{book.emoji}</span>
                      <div className="min-w-0 w-full">
                        <p className={`font-semibold text-sm leading-snug ${book.hasExercises ? 'text-white group-hover:text-amber-400' : 'text-gray-400'}`}>
                          {language === 'en' ? book.titleEn : book.title}
                        </p>
                        {book.author && (
                          <p className="text-xs text-gray-500 mt-0.5">{book.author}</p>
                        )}
                      </div>

                      {book.hasExercises && s && (
                        <div className="w-full flex flex-col gap-1.5 mt-1">
                          <div className="flex flex-col gap-0.5">
                            <div className="flex justify-between text-xs">
                              <span className="text-gray-400">📖 Leçons</span>
                              <span className={lessonPct === 100 ? 'text-green-400 font-semibold' : 'text-gray-400'}>
                                {user ? `${s.readLessons}/${s.totalLessons}` : `${s.totalLessons}`}
                              </span>
                            </div>
                            {user && <ProgressBar value={lessonPct} color="bg-green-500" />}
                          </div>
                          <div className="flex flex-col gap-0.5">
                            <div className="flex justify-between text-xs">
                              <span className="text-gray-400">✓ Exercices</span>
                              <span className={exercisePct === 100 ? 'text-amber-400 font-semibold' : 'text-gray-400'}>
                                {user ? `${s.solvedExercises}/${s.totalExercises}` : `${s.totalExercises}`}
                              </span>
                            </div>
                            {user && <ProgressBar value={exercisePct} color="bg-amber-500" />}
                          </div>
                        </div>
                      )}

                      {book.hasExercises && !s && (
                        <span className="text-xs text-green-400 font-medium">{t('exercisesAvailable')}</span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
