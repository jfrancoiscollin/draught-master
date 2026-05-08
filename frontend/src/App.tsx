import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import Board from './components/Board'
import type { Arrow } from './components/Board'
import AnalysisPanel, { MoveAnnotationsTable } from './components/AnalysisPanel'
import AnalysisText from './components/AnalysisText'
import GameControls, { type PlayerSide } from './components/GameControls'
import MoveList from './components/MoveList'
import ExercisePanel from './components/ExercisePanel'
import ExerciseLibraryPage from './components/ExerciseLibraryPage'
import LessonPanel from './components/LessonPanel'
import ImportGamePanel from './components/ImportGamePanel'
import OpeningCacheBuilder from './components/OpeningCacheBuilder'
import OpeningExplorer from './components/OpeningExplorer'
import LearnFromMistakes from './components/LearnFromMistakes'
import EvalBar from './components/EvalBar'
import UserStatsCard from './components/UserStatsCard'
import Toast from './components/Toast'
import LanguageSelector from './components/LanguageSelector'
import Logo from './components/Logo'
import logoBothSrc from './assets/logo-both.png'
import logoPlaySrc from './assets/logo-play.png'
import BottomSheet from './components/BottomSheet'
import LoginPage from './components/LoginPage'
import { useAuth } from './contexts/AuthContext'
import {
  newGame,
  makeMove,
  analyzePosition,
  checkExercise,
  getExercise,
  getExerciseLegalMovesAtStep,
  undoMove,
  resignGame,
  getAiMove,
  getReadLessons,
  saveGameAnnotations,
} from './api/client'
import type { PdnPosition } from './api/client'
import { getScanEngine, matchHubMove } from './lib/scanEngine'
import {
  annotateGame, computeStats,
  type MoveAnnotation, type GameStats,
  VERDICT_SYMBOL, VERDICT_COLOR,
} from './lib/gameAnnotations'
import {
  EMPTY, WHITE_MAN, WHITE_KING, BLACK_MAN, BLACK_KING,
  sqToRowCol, rcToSq,
} from './types'
import type {
  GameStateResponse,
  MoveData,
  AnalysisResponse,
  ExerciseCheckResponse,