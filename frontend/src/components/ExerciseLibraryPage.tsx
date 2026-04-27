import { useLanguage } from '../i18n/LanguageContext'

interface Book {
  id: string
  title: string
  titleEn: string
  author: string
  category: 'apprentissage' | 'perfectionnement' | 'reference'
  emoji: string
  hasExercises: boolean
}

const BOOKS: Book[] = [
  {
    id: 'dubois_combinaisons',
    title: 'Apprendre les combinaisons',
    titleEn: 'Learning combinations',
    author: 'J-P. Dubois',
    category: 'apprentissage',
    emoji: '💥',
    hasExercises: true,
  },
  {
    id: 'dubois_fins_de_partie',
    title: 'Apprendre les fins de partie',
    titleEn: 'Learning endgames',
    author: 'J-P. Dubois',
    category: 'apprentissage',
    emoji: '🏁',
    hasExercises: false,
  },
  {
    id: 'dubois_sens_du_jeu',
    title: 'Apprendre le sens du jeu',
    titleEn: 'Learning the sense of the game',
    author: 'J-P. Dubois',
    category: 'apprentissage',
    emoji: '🧠',
    hasExercises: false,
  },
  {
    id: 'dubois_perf_combinaisons',
    title: 'Perfectionnement : Combinaisons',
    titleEn: 'Advanced: Combinations',
    author: 'J-P. Dubois',
    category: 'perfectionnement',
    emoji: '⚡',
    hasExercises: false,
  },
  {
    id: 'dubois_perf_sens1',
    title: 'Perfectionnement : Sens du jeu T.1',
    titleEn: 'Advanced: Sense of game Vol.1',
    author: 'J-P. Dubois',
    category: 'perfectionnement',
    emoji: '📘',
    hasExercises: false,
  },
  {
    id: 'dubois_perf_sens2',
    title: 'Perfectionnement : Sens du jeu T.2',
    titleEn: 'Advanced: Sense of game Vol.2',
    author: 'J-P. Dubois',
    category: 'perfectionnement',
    emoji: '📗',
    hasExercises: false,
  },
  {
    id: 'dubois_perf_sens3',
    title: 'Perfectionnement : Sens du jeu T.3',
    titleEn: 'Advanced: Sense of game Vol.3',
    author: 'J-P. Dubois',
    category: 'perfectionnement',
    emoji: '📕',
    hasExercises: false,
  },
  {
    id: 'couttet_ouvertures',
    title: 'Étude des ouvertures',
    titleEn: 'Study of openings',
    author: 'Couttet',
    category: 'reference',
    emoji: '📖',
    hasExercises: false,
  },
  {
    id: 'dubois_referentiel',
    title: 'Référentiel systèmes de jeu',
    titleEn: 'Reference: game systems',
    author: 'J-P. Dubois',
    category: 'reference',
    emoji: '🗂️',
    hasExercises: false,
  },
  {
    id: 'les_enchainements',
    title: 'Les enchaînements',
    titleEn: 'Combination sequences',
    author: '',
    category: 'reference',
    emoji: '🔗',
    hasExercises: false,
  },
]

const CATEGORY_LABELS: Record<string, Record<'fr' | 'en', string>> = {
  apprentissage: { fr: 'Apprentissage', en: 'Learning' },
  perfectionnement: { fr: 'Perfectionnement', en: 'Advanced' },
  reference: { fr: 'Référence', en: 'Reference' },
}

interface ExerciseLibraryPageProps {
  onSelectBook: (bookId: string) => void
}

export default function ExerciseLibraryPage({ onSelectBook }: ExerciseLibraryPageProps) {
  const { t, language } = useLanguage()

  const categories: Book['category'][] = ['apprentissage', 'perfectionnement', 'reference']

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
                {books.map(book => (
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
                    <div className="min-w-0">
                      <p className={`font-semibold text-sm leading-snug ${book.hasExercises ? 'text-white group-hover:text-amber-400' : 'text-gray-400'}`}>
                        {language === 'en' ? book.titleEn : book.title}
                      </p>
                      {book.author && (
                        <p className="text-xs text-gray-500 mt-0.5">{book.author}</p>
                      )}
                    </div>
                    {book.hasExercises && (
                      <span className="text-xs text-green-400 font-medium">{t('exercisesAvailable')}</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
