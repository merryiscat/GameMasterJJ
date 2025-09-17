# **3. UI 디자인 시스템 (UI Design System)**

**참조 문서**: docs/0_architecture.md, docs/2_detailed_functional_specification.md
**작성일**: 2025-09-17
**버전**: 1.0

## **3.1 기본 디자인 토큰 (Design Tokens)**

### **3.1.1 색상 시스템**

**Primary Colors (주요 색상)**
```json
{
  "primary": {
    "50": "#faf7f0",
    "100": "#f3e8d0",
    "200": "#e7d1a2",
    "300": "#d9b571",
    "400": "#cd9b48",
    "500": "#b8832a",
    "600": "#a06824",
    "700": "#855020",
    "800": "#6d4120",
    "900": "#5a361d"
  }
}
```

**Semantic Colors (의미 색상)**
```json
{
  "success": "#10b981",
  "warning": "#f59e0b",
  "error": "#ef4444",
  "info": "#3b82f6",
  "neutral": {
    "50": "#f9fafb",
    "100": "#f3f4f6",
    "200": "#e5e7eb",
    "300": "#d1d5db",
    "400": "#9ca3af",
    "500": "#6b7280",
    "600": "#4b5563",
    "700": "#374151",
    "800": "#1f2937",
    "900": "#111827"
  }
}
```

**TRPG 테마 색상**
```json
{
  "rpg": {
    "gold": "#d4af37",
    "silver": "#c0c0c0",
    "bronze": "#cd7f32",
    "magic": "#9333ea",
    "fire": "#dc2626",
    "ice": "#06b6d4",
    "earth": "#84cc16",
    "dark": "#1f2937",
    "light": "#fbbf24"
  }
}
```

### **3.1.2 타이포그래피**

**Font Families**
- **Primary**: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
- **Display**: "Playfair Display", "Georgia", serif (제목, 로고용)
- **Monospace**: "Fira Code", "Monaco", "Consolas", monospace (코드, 주사위 결과용)

**Font Scale**
```json
{
  "fontSize": {
    "xs": "0.75rem",     // 12px - 보조 정보
    "sm": "0.875rem",    // 14px - 일반 텍스트
    "base": "1rem",      // 16px - 기본 텍스트
    "lg": "1.125rem",    // 18px - 강조 텍스트
    "xl": "1.25rem",     // 20px - 소제목
    "2xl": "1.5rem",     // 24px - 제목
    "3xl": "1.875rem",   // 30px - 큰 제목
    "4xl": "2.25rem"     // 36px - 메인 제목
  },
  "fontWeight": {
    "normal": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700
  }
}
```

### **3.1.3 간격 시스템 (Spacing)**

**8px 기반 그리드 시스템**
```json
{
  "spacing": {
    "0": "0px",
    "1": "4px",      // 0.25rem
    "2": "8px",      // 0.5rem
    "3": "12px",     // 0.75rem
    "4": "16px",     // 1rem
    "5": "20px",     // 1.25rem
    "6": "24px",     // 1.5rem
    "8": "32px",     // 2rem
    "10": "40px",    // 2.5rem
    "12": "48px",    // 3rem
    "16": "64px",    // 4rem
    "20": "80px",    // 5rem
    "24": "96px"     // 6rem
  }
}
```

### **3.1.4 그림자 및 테두리**

**Shadows**
```json
{
  "boxShadow": {
    "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    "base": "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
    "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
    "inner": "inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)"
  }
}
```

**Border Radius**
```json
{
  "borderRadius": {
    "none": "0px",
    "sm": "4px",
    "base": "8px",
    "md": "12px",
    "lg": "16px",
    "xl": "24px",
    "full": "9999px"
  }
}
```

## **3.2 UI 컴포넌트 라이브러리**

### **3.2.1 기본 컴포넌트**

**Button 컴포넌트**
```typescript
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  icon?: ReactNode;
  children: ReactNode;
  onPress: () => void;
}

// Variants
const buttonStyles = {
  primary: {
    backgroundColor: colors.primary[600],
    borderColor: colors.primary[600],
    color: colors.white
  },
  secondary: {
    backgroundColor: colors.neutral[100],
    borderColor: colors.neutral[300],
    color: colors.neutral[900]
  },
  outline: {
    backgroundColor: 'transparent',
    borderColor: colors.primary[600],
    color: colors.primary[600]
  },
  ghost: {
    backgroundColor: 'transparent',
    borderColor: 'transparent',
    color: colors.primary[600]
  },
  danger: {
    backgroundColor: colors.error,
    borderColor: colors.error,
    color: colors.white
  }
};
```

**Input 컴포넌트**
```typescript
interface InputProps {
  label?: string;
  placeholder?: string;
  value: string;
  onChangeText: (text: string) => void;
  error?: string;
  disabled?: boolean;
  type?: 'text' | 'password' | 'number';
  multiline?: boolean;
  numberOfLines?: number;
}
```

**Card 컴포넌트**
```typescript
interface CardProps {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  onPress?: () => void;
  shadow?: boolean;
  padding?: 'sm' | 'md' | 'lg';
}
```

### **3.2.2 TRPG 전용 컴포넌트**

**DiceRoller 컴포넌트**
```typescript
interface DiceRollerProps {
  diceType: '4' | '6' | '8' | '10' | '12' | '20' | '100';
  quantity: number;
  modifier?: number;
  onRoll: (result: DiceResult) => void;
  animate?: boolean;
}

interface DiceResult {
  rolls: number[];
  total: number;
  modifier: number;
  formula: string;
}
```

**CharacterStat 컴포넌트**
```typescript
interface CharacterStatProps {
  label: string;
  value: number;
  modifier?: number;
  max?: number;
  color?: string;
  editable?: boolean;
  onEdit?: (newValue: number) => void;
}
```

**HealthBar 컴포넌트**
```typescript
interface HealthBarProps {
  current: number;
  max: number;
  type: 'hp' | 'mp' | 'xp';
  showNumbers?: boolean;
  animated?: boolean;
}
```

**ChatBubble 컴포넌트**
```typescript
interface ChatBubbleProps {
  message: string;
  sender: 'player' | 'gm' | 'npc';
  timestamp: Date;
  avatar?: string;
  typing?: boolean;
  actions?: Array<{
    label: string;
    onPress: () => void;
  }>;
}
```

### **3.2.3 음성 관련 컴포넌트**

**VoiceInput 컴포넌트**
```typescript
interface VoiceInputProps {
  isListening: boolean;
  onStartListening: () => void;
  onStopListening: () => void;
  transcription?: string;
  confidence?: number;
  error?: string;
}
```

**VoiceOutput 컴포넌트**
```typescript
interface VoiceOutputProps {
  isSpeaking: boolean;
  text: string;
  speed?: number;
  pitch?: number;
  voice?: 'male' | 'female' | 'neutral';
  onStart?: () => void;
  onComplete?: () => void;
}
```

**AudioVisualizer 컴포넌트**
```typescript
interface AudioVisualizerProps {
  isActive: boolean;
  frequencyData?: number[];
  color?: string;
  barCount?: number;
  height?: number;
}
```

## **3.3 화면 구성 및 레이아웃**

### **3.3.1 메인 게임 화면**

**GameScreen 레이아웃**
```
┌─────────────────────────────────────────┐
│ Header: Game Title + Settings Button    │
├─────────────────────────────────────────┤
│                                         │
│           Chat Area                     │
│     (Scrollable Message List)          │
│                                         │
│                                         │
├─────────────────────────────────────────┤
│ Input Area: Text Input + Voice Button   │
├─────────────────────────────────────────┤
│ Bottom Tab: Character | Dice | Menu     │
└─────────────────────────────────────────┘
```

**컴포넌트 구조**
- Header: 고정 높이 64px
- Chat Area: 가변 높이 (화면의 70%)
- Input Area: 고정 높이 80px
- Bottom Tab: 고정 높이 60px

### **3.3.2 캐릭터 시트 화면**

**CharacterSheet 레이아웃**
```
┌─────────────────────────────────────────┐
│ Character Name + Level + Portrait       │
├─────────────────────────────────────────┤
│ Ability Scores (STR, DEX, CON...)      │
├─────────────────────────────────────────┤
│ Skills & Proficiencies                 │
├─────────────────────────────────────────┤
│ Equipment & Inventory                   │
├─────────────────────────────────────────┤
│ Spells & Abilities                     │
└─────────────────────────────────────────┘
```

### **3.3.3 설정 화면**

**Settings 레이아웃**
- 음성 설정 (On/Off, 속도, 음성 선택)
- 게임 설정 (자동 저장, 알림)
- 디스플레이 설정 (다크모드, 폰트 크기)
- 데이터 관리 (백업, 복원, 초기화)

## **3.4 반응형 및 접근성 고려사항**

### **3.4.1 반응형 디자인**

**Breakpoints**
```json
{
  "screens": {
    "sm": "640px",   // 모바일 가로
    "md": "768px",   // 태블릿 세로
    "lg": "1024px",  // 태블릿 가로
    "xl": "1280px"   // 데스크톱
  }
}
```

**모바일 우선 설계**
- 기본: 360px x 640px (모바일 세로)
- 최소 터치 영역: 44px x 44px
- 여백: 최소 16px
- 텍스트 가독성: 최소 14px

**태블릿 최적화**
- Chat Area: 2-column 레이아웃 (대화 + 캐릭터 정보)
- Side Panel: 영구 표시 가능
- 더 큰 터치 영역 및 간격

### **3.4.2 접근성 (Accessibility)**

**시각 접근성**
- 색상 대비비: WCAG 2.1 AA 준수 (4.5:1 이상)
- 색상에만 의존하지 않는 정보 전달
- 폰트 크기 확대 지원 (최대 200%)
- 다크모드 지원

**청각 접근성**
- 모든 음성 출력에 대한 텍스트 대안
- 시각적 음성 인디케이터
- 진동 피드백 옵션

**운동 능력 접근성**
- 터치 영역 최소 크기 보장
- 길게 누르기/제스처 대신 버튼 제공
- 음성 입력으로 모든 기능 접근 가능

**인지 접근성**
- 명확하고 일관된 내비게이션
- 오류 예방 및 복구 지원
- 진행 상황 및 상태 명확 표시

## **3.5 애니메이션 및 트랜지션**

### **3.5.1 기본 애니메이션**

**Duration (지속 시간)**
```json
{
  "duration": {
    "fast": "150ms",      // 버튼 호버, 포커스
    "normal": "300ms",    // 페이지 전환, 모달
    "slow": "500ms",      // 복잡한 상태 변화
    "extra-slow": "1000ms" // 주사위 굴리기
  }
}
```

**Easing (이징)**
```json
{
  "easing": {
    "linear": "linear",
    "ease-in": "cubic-bezier(0.4, 0, 1, 1)",
    "ease-out": "cubic-bezier(0, 0, 0.2, 1)",
    "ease-in-out": "cubic-bezier(0.4, 0, 0.2, 1)",
    "bounce": "cubic-bezier(0.68, -0.55, 0.265, 1.55)"
  }
}
```

### **3.5.2 특수 애니메이션**

**DiceRoll 애니메이션**
- 주사위 회전: 3D 변환
- 결과 나타남: Scale + Fade In
- 총 시간: 1-2초
- 사운드 효과와 동기화

**ChatBubble 애니메이션**
- 새 메시지: Slide Up + Fade In
- 타이핑 인디케이터: Pulse 애니메이션
- 음성 시각화: Real-time frequency bars

**VoiceInput 애니메이션**
- 듣기 상태: Pulse ring
- 인식 중: Wave animation
- 완료: Checkmark with bounce

## **3.6 다크모드 및 테마**

### **3.6.1 다크 테마 색상**

```json
{
  "dark": {
    "primary": {
      "50": "#1f1611",
      "100": "#2a1f17",
      "500": "#d9b571",
      "600": "#e7d1a2"
    },
    "neutral": {
      "50": "#111827",
      "100": "#1f2937",
      "200": "#374151",
      "800": "#f3f4f6",
      "900": "#f9fafb"
    },
    "surface": {
      "primary": "#1f2937",
      "secondary": "#374151",
      "tertiary": "#4b5563"
    }
  }
}
```

### **3.6.2 테마 전환**

- 시스템 설정 따르기 (기본값)
- 수동 전환 옵션
- 부드러운 색상 전환 애니메이션
- 모든 컴포넌트 자동 적용

## **3.7 구현 우선순위**

### **Phase 1 (MVP 핵심)**
1. **기본 컴포넌트**: Button, Input, Card, Text
2. **메인 화면**: GameScreen, ChatBubble, VoiceInput
3. **기본 색상**: Primary, Neutral, Semantic colors
4. **기본 애니메이션**: Fade, Slide transitions

### **Phase 2 (기능 확장)**
1. **TRPG 컴포넌트**: DiceRoller, CharacterStat, HealthBar
2. **캐릭터 화면**: CharacterSheet 전체 구현
3. **음성 컴포넌트**: VoiceOutput, AudioVisualizer
4. **접근성**: 기본 접근성 기능 구현

### **Phase 3 (사용성 향상)**
1. **다크모드**: 완전한 다크 테마 구현
2. **반응형**: 태블릿 최적화 레이아웃
3. **고급 애니메이션**: 3D 주사위, 복잡한 전환
4. **미세 조정**: 세밀한 스타일링 및 폴리시

### **Phase 4 (최적화)**
1. **성능 최적화**: 애니메이션 성능, 메모리 사용량
2. **접근성 완성**: WCAG 2.1 AAA 레벨 준수
3. **고급 테마**: 사용자 정의 테마 지원
4. **브랜딩**: 일관된 브랜드 아이덴티티 완성

## **3.8 디자인 토큰 관리**

### **3.8.1 파일 구조**
```
design-tokens/
├── colors.json
├── typography.json
├── spacing.json
├── shadows.json
├── animations.json
└── themes/
    ├── light.json
    └── dark.json
```

### **3.8.2 토큰 변환**
- JSON → React Native StyleSheet
- JSON → CSS Custom Properties (웹 버전용)
- 자동 타입 생성 (TypeScript)
- 디자인 도구 동기화 (Figma)

### **3.8.3 일관성 유지**
- ESLint 규칙: 하드코딩된 색상/크기 금지
- Storybook: 컴포넌트 문서화
- 자동 테스트: 접근성 및 디자인 규칙 검증
- 디자인 리뷰: PR 단계에서 디자인 토큰 사용 검토