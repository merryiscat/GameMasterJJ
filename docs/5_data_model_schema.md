# **5. 데이터 모델 스키마 (Data Model Schema)**

**참조 문서**: docs/0_architecture.md, docs/4_api_specification.md
**작성일**: 2025-09-17
**버전**: 1.0

## **5.1 데이터 아키텍처 개요**

**데이터베이스**: SQLite (로컬), PostgreSQL (확장 시)
**ORM**: SQLAlchemy (Python)
**마이그레이션**: Alembic
**캐싱**: Redis (선택적)
**파일 저장소**: 로컬 파일 시스템

### **5.1.1 데이터 분류**

**게임 상태 데이터 (SQLite)**
- 캐릭터 정보
- 게임 세션 데이터
- 인벤토리 및 아이템
- 게임 진행 상황

**콘텐츠 데이터 (JSON 파일)**
- 스토리렛 정의
- 세계관 설정
- NPC 정보
- 아이템 템플릿

**임시 데이터 (메모리/Redis)**
- 에이전트 상태
- 활성 세션 정보
- 캐시된 응답

## **5.2 핵심 테이블 스키마**

### **5.2.1 게임 세션 (game_sessions)**

```sql
CREATE TABLE game_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL,
    character_id UUID NOT NULL,
    session_name VARCHAR(255) NOT NULL,
    current_location VARCHAR(255),
    world_state JSONB DEFAULT '{}',
    active_storylets JSONB DEFAULT '[]',
    flags JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_game_sessions_character ON game_sessions(character_id);
CREATE INDEX idx_game_sessions_story ON game_sessions(story_id);
CREATE INDEX idx_game_sessions_activity ON game_sessions(last_activity);
```

### **5.2.2 캐릭터 정보 (characters)**

```sql
CREATE TABLE characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    class VARCHAR(50) NOT NULL,
    race VARCHAR(50),
    level INTEGER DEFAULT 1,
    experience INTEGER DEFAULT 0,

    -- 기본 능력치
    strength INTEGER DEFAULT 10,
    dexterity INTEGER DEFAULT 10,
    constitution INTEGER DEFAULT 10,
    intelligence INTEGER DEFAULT 10,
    wisdom INTEGER DEFAULT 10,
    charisma INTEGER DEFAULT 10,

    -- 파생 능력치
    armor_class INTEGER DEFAULT 10,
    max_hit_points INTEGER DEFAULT 8,
    current_hit_points INTEGER DEFAULT 8,
    temporary_hit_points INTEGER DEFAULT 0,
    speed INTEGER DEFAULT 30,
    proficiency_bonus INTEGER DEFAULT 2,

    -- 추가 속성
    skills JSONB DEFAULT '{}',
    proficiencies JSONB DEFAULT '[]',
    languages JSONB DEFAULT '[]',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_characters_name ON characters(name);
CREATE INDEX idx_characters_level ON characters(level);
```

### **5.2.3 인벤토리 (inventory_items)**

```sql
CREATE TABLE inventory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    item_template_id VARCHAR(100) NOT NULL,
    quantity INTEGER DEFAULT 1,
    is_equipped BOOLEAN DEFAULT FALSE,
    custom_properties JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_inventory_character ON inventory_items(character_id);
CREATE INDEX idx_inventory_equipped ON inventory_items(character_id, is_equipped);
```

### **5.2.4 채팅 히스토리 (chat_messages)**

```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    sender VARCHAR(20) NOT NULL, -- 'player', 'gm', 'npc'
    sender_id VARCHAR(100), -- NPC ID 등
    content TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text', -- 'text', 'action', 'dice_roll', 'system'
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chat_session ON chat_messages(session_id, timestamp);
CREATE INDEX idx_chat_sender ON chat_messages(sender, sender_id);
```

### **5.2.5 주사위 굴림 기록 (dice_rolls)**

```sql
CREATE TABLE dice_rolls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    message_id UUID REFERENCES chat_messages(id) ON DELETE SET NULL,
    formula VARCHAR(100) NOT NULL,
    individual_rolls JSONB NOT NULL, -- [4, 6, 2]
    modifier INTEGER DEFAULT 0,
    total INTEGER NOT NULL,
    reason TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_dice_session ON dice_rolls(session_id, timestamp);
```

### **5.2.6 상태 효과 (status_effects)**

```sql
CREATE TABLE status_effects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    duration_remaining INTEGER, -- seconds, NULL for permanent
    effect_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_status_character ON status_effects(character_id);
```

### **5.2.7 세이브 데이터 (save_games)**

```sql
CREATE TABLE save_games (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    save_slot VARCHAR(50) NOT NULL,
    description TEXT,
    game_state JSONB NOT NULL,
    character_state JSONB NOT NULL,
    inventory_state JSONB NOT NULL,
    chat_history JSONB,
    screenshot_path VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_saves_session ON save_games(session_id, save_slot);
CREATE UNIQUE INDEX idx_saves_unique ON save_games(session_id, save_slot);
```

## **5.3 JSON 콘텐츠 스키마**

### **5.3.1 스토리렛 정의 (storylets.json)**

```typescript
interface Storylet {
  id: string;
  title: string;
  description: string;
  tags: string[];

  preconditions: {
    location?: string | string[];
    flags?: string[]; // "flag_name" or "!flag_name" for negation
    stats?: {
      [statName: string]: {
        min?: number;
        max?: number;
      };
    };
    items?: string[];
    relationships?: {
      [npcId: string]: 'hostile' | 'neutral' | 'friendly' | 'allied';
    };
  };

  postconditions: {
    flags?: string[];
    stats?: {
      [statName: string]: number; // change amount
    };
    items?: {
      add?: string[];
      remove?: string[];
    };
    relationships?: {
      [npcId: string]: string; // new relationship level
    };
    location?: string;
  };

  content: {
    opening: string;
    choices: Array<{
      text: string;
      requirements?: {
        stats?: { [key: string]: number };
        items?: string[];
      };
      consequences: string[];
      probability?: number; // 0.0-1.0, default 1.0
    }>;
    followUp?: string; // next storylet ID
  };

  abstractActions?: Array<{
    type: string;
    parameters: Record<string, any>;
    weight: number;
  }>;
}
```

### **5.3.2 아이템 템플릿 (item_templates.json)**

```typescript
interface ItemTemplate {
  id: string;
  name: string;
  description: string;
  type: 'weapon' | 'armor' | 'consumable' | 'tool' | 'treasure' | 'misc';
  rarity: 'common' | 'uncommon' | 'rare' | 'very_rare' | 'legendary';
  value: number; // in gold pieces
  weight: number; // in pounds

  properties: string[]; // 'magical', 'silvered', 'finesse', etc.

  // Weapon specific
  damage?: {
    dice: string; // "1d8"
    type: 'slashing' | 'piercing' | 'bludgeoning' | 'fire' | 'cold' | 'etc';
  };

  // Armor specific
  armorClass?: {
    base: number;
    dexBonus?: boolean;
    maxDexBonus?: number;
  };

  // Consumable specific
  consumable?: {
    uses: number;
    effect: {
      healing?: number;
      statusEffect?: string;
      duration?: number;
    };
  };

  // Equipment bonuses
  bonuses?: {
    stats?: { [statName: string]: number };
    skills?: { [skillName: string]: number };
    savingThrows?: { [saveName: string]: number };
  };
}
```

### **5.3.3 NPC 정의 (npcs.json)**

```typescript
interface NPC {
  id: string;
  name: string;
  description: string;
  personality: string;
  motivation: string;

  appearance: {
    physicalDescription: string;
    clothing: string;
    mannerisms: string;
  };

  voice: {
    tone: string;
    speechPattern: string;
    vocabulary: 'simple' | 'common' | 'educated' | 'archaic';
  };

  stats?: {
    level: number;
    hitPoints: number;
    armorClass: number;
    abilities: Record<string, number>;
  };

  relationships: {
    defaultDisposition: 'hostile' | 'unfriendly' | 'neutral' | 'friendly' | 'helpful';
    factionsAndAllies: string[];
    enemies: string[];
  };

  knowledge: {
    commonKnowledge: string[];
    secretInformation: string[];
    rumors: string[];
  };

  questHooks?: Array<{
    questId: string;
    triggerCondition: string;
    description: string;
  }>;
}
```

### **5.3.4 세계관 정보 (lore.json)**

```typescript
interface LoreEntry {
  id: string;
  category: 'location' | 'history' | 'religion' | 'politics' | 'culture' | 'magic';
  title: string;
  summary: string;
  content: string;

  knowledgeLevel: 'common' | 'specialized' | 'secret' | 'forbidden';

  relatedEntries: string[]; // IDs of related lore entries
  tags: string[];

  playerDiscoverable: boolean;
  spoilerLevel: 'none' | 'minor' | 'major' | 'ending';

  sources: Array<{
    npcId?: string;
    locationId?: string;
    itemId?: string;
    condition: string;
  }>;
}
```

## **5.4 에이전트 상태 스키마**

### **5.4.1 세션별 에이전트 메모리 (Redis)**

```typescript
interface AgentSessionMemory {
  sessionId: string;
  agentType: 'triage' | 'narrator' | 'rules_keeper' | 'npc_interaction' | 'lore_keeper';

  conversationHistory: Array<{
    timestamp: string;
    input: string;
    output: string;
    context: Record<string, any>;
  }>;

  currentContext: {
    activeNPCs: string[];
    currentMood: string;
    recentEvents: string[];
    playerKnowledge: string[];
  };

  temporaryMemory: Record<string, any>; // 세션 중 임시 정보

  lastActivity: string;
  ttl: number; // Time to live in seconds
}
```

### **5.4.2 글로벌 에이전트 설정**

```typescript
interface AgentConfiguration {
  agentType: string;

  model: {
    name: string;
    temperature: number;
    maxTokens: number;
    topP: number;
  };

  systemPrompt: string;

  tools: Array<{
    name: string;
    description: string;
    parameters: Record<string, any>;
  }>;

  guardrails: Array<{
    type: 'input' | 'output';
    rule: string;
    action: 'block' | 'warn' | 'modify';
  }>;

  handoffTargets: string[];
}
```

## **5.5 데이터 검증 및 제약조건**

### **5.5.1 Pydantic 모델**

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class CharacterStats(BaseModel):
    strength: int = Field(ge=3, le=20, default=10)
    dexterity: int = Field(ge=3, le=20, default=10)
    constitution: int = Field(ge=3, le=20, default=10)
    intelligence: int = Field(ge=3, le=20, default=10)
    wisdom: int = Field(ge=3, le=20, default=10)
    charisma: int = Field(ge=3, le=20, default=10)

class Character(BaseModel):
    id: Optional[str] = None
    name: str = Field(min_length=1, max_length=100)
    class_name: str = Field(alias='class', min_length=1, max_length=50)
    race: Optional[str] = Field(max_length=50)
    level: int = Field(ge=1, le=20, default=1)
    experience: int = Field(ge=0, default=0)
    stats: CharacterStats
    max_hit_points: int = Field(ge=1, default=8)
    current_hit_points: int = Field(ge=0)
    armor_class: int = Field(ge=5, le=30, default=10)

    @validator('current_hit_points')
    def validate_current_hp(cls, v, values):
        max_hp = values.get('max_hit_points', 8)
        if v > max_hp:
            raise ValueError('Current HP cannot exceed maximum HP')
        return v

class GameSession(BaseModel):
    id: Optional[str] = None
    story_id: str
    character_id: str
    session_name: str = Field(min_length=1, max_length=255)
    current_location: Optional[str] = Field(max_length=255)
    world_state: Dict[str, Any] = Field(default_factory=dict)
    active_storylets: List[str] = Field(default_factory=list)
    flags: List[str] = Field(default_factory=list)
    is_active: bool = True

class DiceRoll(BaseModel):
    formula: str = Field(regex=r'^\d+d\d+([+-]\d+)?$')
    individual_rolls: List[int]
    modifier: int = 0
    total: int
    reason: Optional[str] = Field(max_length=255)

    @validator('total')
    def validate_total(cls, v, values):
        rolls = values.get('individual_rolls', [])
        modifier = values.get('modifier', 0)
        expected_total = sum(rolls) + modifier
        if v != expected_total:
            raise ValueError(f'Total {v} does not match rolls {rolls} + {modifier}')
        return v
```

### **5.5.2 데이터베이스 제약조건**

```sql
-- 캐릭터 능력치 제약
ALTER TABLE characters ADD CONSTRAINT check_ability_scores
CHECK (
    strength BETWEEN 3 AND 20 AND
    dexterity BETWEEN 3 AND 20 AND
    constitution BETWEEN 3 AND 20 AND
    intelligence BETWEEN 3 AND 20 AND
    wisdom BETWEEN 3 AND 20 AND
    charisma BETWEEN 3 AND 20
);

-- 레벨 제약
ALTER TABLE characters ADD CONSTRAINT check_level
CHECK (level BETWEEN 1 AND 20);

-- 체력 제약
ALTER TABLE characters ADD CONSTRAINT check_hit_points
CHECK (
    max_hit_points >= 1 AND
    current_hit_points >= 0 AND
    current_hit_points <= max_hit_points + temporary_hit_points
);

-- 인벤토리 수량 제약
ALTER TABLE inventory_items ADD CONSTRAINT check_quantity
CHECK (quantity > 0);

-- 메시지 송신자 제약
ALTER TABLE chat_messages ADD CONSTRAINT check_sender
CHECK (sender IN ('player', 'gm', 'npc', 'system'));
```

## **5.6 데이터 마이그레이션 스크립트**

### **5.6.1 Alembic 마이그레이션 예제**

```python
"""Create initial tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-09-17 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create characters table
    op.create_table('characters',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('class', sa.String(length=50), nullable=False),
        sa.Column('race', sa.String(length=50), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False, default=1),
        sa.Column('experience', sa.Integer(), nullable=False, default=0),
        # ... 모든 컬럼 정의
        sa.PrimaryKeyConstraint('id')
    )

    # Create game_sessions table
    op.create_table('game_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('story_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('character_id', postgresql.UUID(as_uuid=True), nullable=False),
        # ... 모든 컬럼 정의
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], )
    )

    # Create indexes
    op.create_index('idx_characters_name', 'characters', ['name'])
    op.create_index('idx_game_sessions_character', 'game_sessions', ['character_id'])

def downgrade():
    op.drop_index('idx_game_sessions_character')
    op.drop_index('idx_characters_name')
    op.drop_table('game_sessions')
    op.drop_table('characters')
```

## **5.7 성능 최적화**

### **5.7.1 인덱싱 전략**

```sql
-- 복합 인덱스 (자주 함께 쿼리되는 컬럼들)
CREATE INDEX idx_chat_session_sender ON chat_messages(session_id, sender, timestamp);
CREATE INDEX idx_inventory_character_equipped ON inventory_items(character_id, is_equipped);

-- 부분 인덱스 (조건부 인덱스)
CREATE INDEX idx_active_sessions ON game_sessions(last_activity) WHERE is_active = true;
CREATE INDEX idx_equipped_items ON inventory_items(character_id) WHERE is_equipped = true;

-- JSONB 인덱스
CREATE INDEX idx_world_state_location ON game_sessions USING gin ((world_state->'location'));
CREATE INDEX idx_item_properties ON inventory_items USING gin (custom_properties);
```

### **5.7.2 쿼리 최적화**

```python
# 효율적인 세션 데이터 로드
def load_game_session_with_character(session_id: str):
    return db.query(GameSession)\
        .options(
            joinedload(GameSession.character),
            selectinload(GameSession.chat_messages)
                .options(load_only('content', 'sender', 'timestamp'))
        )\
        .filter(GameSession.id == session_id)\
        .first()

# 배치 인벤토리 로드
def load_character_inventory(character_id: str):
    return db.query(InventoryItem)\
        .options(joinedload(InventoryItem.template))\
        .filter(InventoryItem.character_id == character_id)\
        .all()
```

### **5.7.3 캐싱 전략**

```python
import redis
from functools import wraps
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expiry=300):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            cached = redis_client.get(cache_key)

            if cached:
                return json.loads(cached)

            result = func(*args, **kwargs)
            redis_client.setex(cache_key, expiry, json.dumps(result))
            return result
        return wrapper
    return decorator

@cache_result(expiry=600)
def get_storylets_for_location(location: str):
    # 위치별 스토리렛 조회 (자주 호출되지만 자주 변경되지 않음)
    pass
```

## **5.8 백업 및 복구 전략**

### **5.8.1 자동 백업**

```python
import sqlite3
import shutil
from datetime import datetime, timedelta
import os

def create_automatic_backup():
    """매 시간마다 자동 백업 생성"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    source_db = "gamemaster.db"
    backup_path = f"backups/gamemaster_backup_{timestamp}.db"

    # SQLite 온라인 백업
    source_conn = sqlite3.connect(source_db)
    backup_conn = sqlite3.connect(backup_path)

    source_conn.backup(backup_conn)

    source_conn.close()
    backup_conn.close()

    # 7일 이상 된 백업 삭제
    cleanup_old_backups(days=7)

def cleanup_old_backups(days=7):
    """오래된 백업 파일 정리"""
    backup_dir = "backups"
    cutoff_date = datetime.now() - timedelta(days=days)

    for filename in os.listdir(backup_dir):
        if filename.startswith("gamemaster_backup_"):
            file_path = os.path.join(backup_dir, filename)
            file_time = datetime.fromtimestamp(os.path.getctime(file_path))

            if file_time < cutoff_date:
                os.remove(file_path)
```

### **5.8.2 데이터 무결성 검증**

```python
def verify_database_integrity():
    """데이터베이스 무결성 검증"""
    checks = []

    # Foreign key 무결성 확인
    orphaned_sessions = db.execute("""
        SELECT COUNT(*) FROM game_sessions gs
        WHERE NOT EXISTS (
            SELECT 1 FROM characters c WHERE c.id = gs.character_id
        )
    """).scalar()

    checks.append(('orphaned_sessions', orphaned_sessions == 0))

    # 체력 제약 확인
    invalid_hp = db.execute("""
        SELECT COUNT(*) FROM characters
        WHERE current_hit_points > max_hit_points + temporary_hit_points
    """).scalar()

    checks.append(('invalid_hitpoints', invalid_hp == 0))

    # 인벤토리 일관성 확인
    invalid_inventory = db.execute("""
        SELECT COUNT(*) FROM inventory_items
        WHERE quantity <= 0
    """).scalar()

    checks.append(('invalid_inventory', invalid_inventory == 0))

    return all(check[1] for check in checks), checks
```

이제 데이터 모델 스키마 문서를 완성했습니다. 계속해서 나머지 문서들을 작성하겠습니다.