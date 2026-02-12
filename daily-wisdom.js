const STORAGE_KEY = 'daily-wisdom-tags-v1';
const DATA_URL = './daily-wisdom-data.json';
const CONFIG_SERVER = 'http://127.0.0.1:9876';

// Loaded dynamically from config server
let SUPABASE_URL = '';
let SUPABASE_ANON_KEY = '';

const fallbackData = [
  {
    id: 1,
    title: 'Reliable local-first apps with CRDTs',
    hnUrl: 'https://news.ycombinator.com/item?id=1',
    score: 342,
    commentCount: 87,
    author: 'synthwave',
    processedAt: '2026-02-10',
    article: {
      url: 'https://example.com/crdts',
      summary: 'A deep dive into conflict-free replicated data types and why local-first design unlocks resilience for teams.',
      readingTime: '8 min'
    },
    topComments: [
      { text: 'CRDTs finally make collaboration predictable without giant merge conflicts.', score: 124 },
      { text: 'Local-first is the only approach that feels human at scale.', score: 98 }
    ],
    categories: ['AI/ML', 'DevOps'],
    tags: ['local-first', 'reliability'],
    cluster: 'Distributed systems'
  },
  {
    id: 2,
    title: 'The hidden cost of vector search infrastructure',
    hnUrl: 'https://news.ycombinator.com/item?id=2',
    score: 211,
    commentCount: 64,
    author: 'latency_lad',
    processedAt: '2026-02-09',
    article: {
      url: 'https://example.com/vector-search',
      summary: 'Teams are overspending on embeddings and indexing. This analysis maps cost per query and suggests leaner stacks.',
      readingTime: '6 min'
    },
    topComments: [
      { text: 'We cut spend 60% by caching clusters and pruning dimensions.', score: 80 },
      { text: 'The real cost is in streaming ingestion not storage.', score: 52 }
    ],
    categories: ['AI/ML', 'Databases'],
    tags: ['infra', 'embeddings'],
    cluster: 'AI infrastructure'
  },
  {
    id: 3,
    title: 'Why security teams are building internal browsers',
    hnUrl: 'https://news.ycombinator.com/item?id=3',
    score: 178,
    commentCount: 51,
    author: 'safelink',
    processedAt: '2026-02-08',
    article: {
      url: 'https://example.com/secure-browser',
      summary: 'A look at controlled browsing environments to prevent data exfiltration and shadow SaaS usage.',
      readingTime: '7 min'
    },
    topComments: [
      { text: 'Browser isolation is the new EDR.', score: 67 },
      { text: 'We still need identity-first security layers.', score: 42 }
    ],
    categories: ['Security'],
    tags: ['browser', 'risk'],
    cluster: 'Enterprise security'
  },
  {
    id: 4,
    title: 'Designing a weekly shipping cadence for startups',
    hnUrl: 'https://news.ycombinator.com/item?id=4',
    score: 132,
    commentCount: 29,
    author: 'shipit',
    processedAt: '2026-02-06',
    article: {
      url: 'https://example.com/shipping-cadence',
      summary: 'Operational patterns that keep small teams shipping without burning out.',
      readingTime: '5 min'
    },
    topComments: [
      { text: 'Weekly releases force clarity on what matters.', score: 38 },
      { text: 'Ship in slices, not epics.', score: 30 }
    ],
    categories: ['Startups', 'Career'],
    tags: ['execution', 'teams'],
    cluster: 'Product ops'
  },
  {
    id: 5,
    title: 'The state of post-quantum crypto tooling',
    hnUrl: 'https://news.ycombinator.com/item?id=5',
    score: 298,
    commentCount: 91,
    author: 'cipher',
    processedAt: '2026-02-10',
    article: {
      url: 'https://example.com/post-quantum',
      summary: 'Benchmarks of hybrid TLS stacks and migration timelines for regulated industries.',
      readingTime: '9 min'
    },
    topComments: [
      { text: 'Hybrid is the only practical path until standards settle.', score: 112 },
      { text: 'Interop is still a mess across vendors.', score: 73 }
    ],
    categories: ['Security', 'Web Development'],
    tags: ['crypto', 'standards'],
    cluster: 'Security futures'
  },
  {
    id: 6,
    title: 'From notebooks to production: an LLM eval pipeline',
    hnUrl: 'https://news.ycombinator.com/item?id=6',
    score: 245,
    commentCount: 77,
    author: 'evals',
    processedAt: '2026-02-07',
    article: {
      url: 'https://example.com/llm-evals',
      summary: 'Practical steps to formalize evaluation criteria and regression testing for LLM-driven products.',
      readingTime: '10 min'
    },
    topComments: [
      { text: 'We needed a rubric before we needed a dataset.', score: 90 },
      { text: 'Continuous evals exposed prompt drift in week one.', score: 64 }
    ],
    categories: ['AI/ML', 'Web Development'],
    tags: ['evals', 'quality'],
    cluster: 'AI product quality'
  },
  {
    id: 7,
    title: 'Ask HN: best way to archive internal knowledge?',
    hnUrl: 'https://news.ycombinator.com/item?id=7',
    score: 167,
    commentCount: 58,
    author: 'archivist',
    processedAt: '2026-02-04',
    article: {
      url: 'https://example.com/knowledge-archive',
      summary: 'A roundup of lightweight tooling to preserve context and lessons learned without a massive wiki.',
      readingTime: '4 min'
    },
    topComments: [
      { text: 'People forget to write unless the process is lightweight.', score: 55 },
      { text: 'Automate summaries from meeting notes.', score: 49 }
    ],
    categories: ['Ask HN', 'Career'],
    tags: ['knowledge', 'process'],
    cluster: 'Org memory'
  },
  {
    id: 8,
    title: 'Show HN: a lightning-fast offline docs reader',
    hnUrl: 'https://news.ycombinator.com/item?id=8',
    score: 119,
    commentCount: 33,
    author: 'offline',
    processedAt: '2026-02-03',
    article: {
      url: 'https://example.com/offline-docs',
      summary: 'A desktop app for caching and searching docs with zero latency.',
      readingTime: '3 min'
    },
    topComments: [
      { text: 'We need this for airgapped environments.', score: 35 },
      { text: 'Search ranking is impressively snappy.', score: 21 }
    ],
    categories: ['Show HN', 'Web Development'],
    tags: ['docs', 'offline'],
    cluster: 'Developer tooling'
  },
  {
    id: 9,
    title: 'Debugging at scale: what SREs actually want',
    hnUrl: 'https://news.ycombinator.com/item?id=9',
    score: 190,
    commentCount: 70,
    author: 'pager',
    processedAt: '2026-02-09',
    article: {
      url: 'https://example.com/sre-debug',
      summary: 'Observability teams are asking for narrative traces and causal graphs, not just metrics dashboards.',
      readingTime: '7 min'
    },
    topComments: [
      { text: 'We want the story, not the graph.', score: 66 },
      { text: 'Root cause annotations save hours per incident.', score: 51 }
    ],
    categories: ['DevOps', 'Databases'],
    tags: ['observability', 'sre'],
    cluster: 'Reliability'
  },
  {
    id: 10,
    title: 'Career ladders that work for ICs and managers',
    hnUrl: 'https://news.ycombinator.com/item?id=10',
    score: 140,
    commentCount: 41,
    author: 'growth',
    processedAt: '2026-02-01',
    article: {
      url: 'https://example.com/career-ladders',
      summary: 'A pragmatic template for leveling that avoids politics and keeps teams aligned.',
      readingTime: '5 min'
    },
    topComments: [
      { text: 'Transparent rubrics reduce churn.', score: 44 },
      { text: 'Leveling should be about impact not tenure.', score: 29 }
    ],
    categories: ['Career'],
    tags: ['growth', 'people'],
    cluster: 'Org design'
  },
  {
    id: 11,
    title: 'Database branching for faster CI',
    hnUrl: 'https://news.ycombinator.com/item?id=11',
    score: 156,
    commentCount: 49,
    author: 'forked',
    processedAt: '2026-02-08',
    article: {
      url: 'https://example.com/db-branching',
      summary: 'Snapshotting data environments lets teams ship migrations without fear.',
      readingTime: '6 min'
    },
    topComments: [
      { text: 'Branching saved us hours of manual QA.', score: 47 },
      { text: 'We still need better seeded data.', score: 33 }
    ],
    categories: ['Databases', 'DevOps'],
    tags: ['ci', 'migrations'],
    cluster: 'Developer tooling'
  },
  {
    id: 12,
    title: 'Ask HN: what is the future of APIs?',
    hnUrl: 'https://news.ycombinator.com/item?id=12',
    score: 203,
    commentCount: 86,
    author: 'api_future',
    processedAt: '2026-02-10',
    article: {
      url: 'https://example.com/api-future',
      summary: 'Developers debate the shift from REST to event-driven and AI-native interfaces.',
      readingTime: '8 min'
    },
    topComments: [
      { text: 'APIs should become contracts with stronger semantics.', score: 72 },
      { text: 'We need better toolchains for event-driven integration.', score: 61 }
    ],
    categories: ['Ask HN', 'Web Development'],
    tags: ['api', 'events'],
    cluster: 'Platform evolution'
  }
];

let data = [];
let baseDate = new Date();

const state = {
  view: 'card',
  search: '',
  categories: new Set(),
  clusters: new Set(),
  dateRange: 'all',
  datePicker: '',
  selectedId: null,
  groupByCluster: false,
  calendarMonth: baseDate.getMonth(),
  calendarYear: baseDate.getFullYear(),
  scoreMin: '',
  commentsMin: '',
  author: ''
};

const elements = {
  cards: document.getElementById('cards'),
  list: document.getElementById('list'),
  listBody: document.querySelector('#list tbody'),
  resultTitle: document.getElementById('resultTitle'),
  resultCount: document.getElementById('resultCount'),
  categoryPills: document.getElementById('categoryPills'),
  clusterPills: document.getElementById('clusterPills'),
  clusterBar: document.getElementById('clusterBar'),
  tagPills: document.getElementById('tagPills'),
  drawer: document.getElementById('drawer'),
  drawerTitle: document.getElementById('drawerTitle'),
  drawerMeta: document.getElementById('drawerMeta'),
  drawerArticle: document.getElementById('drawerArticle'),
  drawerLink: document.getElementById('drawerLink'),
  drawerComments: document.getElementById('drawerComments'),
  drawerTags: document.getElementById('drawerTags'),
  tagInput: document.getElementById('tagInput'),
  search: document.getElementById('search'),
  clearSearch: document.getElementById('clearSearch'),
  datePicker: document.getElementById('datePicker'),
  clusterToggle: document.getElementById('clusterToggle'),
  calendarGrid: document.getElementById('calendarGrid'),
  monthLabel: document.getElementById('monthLabel'),
  prevMonth: document.getElementById('prevMonth'),
  nextMonth: document.getElementById('nextMonth'),
  timelineStrip: document.getElementById('timelineStrip'),
  scoreMin: document.getElementById('scoreMin'),
  commentsMin: document.getElementById('commentsMin'),
  authorFilter: document.getElementById('authorFilter'),
  resetFilters: document.getElementById('resetFilters'),
  exportJson: document.getElementById('exportJson'),
  exportCsv: document.getElementById('exportCsv')
};

const viewButtons = document.querySelectorAll('.view-toggle .chip[data-view]');
const dateButtons = document.querySelectorAll('[data-range]');

function formatDate(value) {
  const date = new Date(value + 'T00:00:00');
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function toKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function loadSavedTags() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (error) {
    return {};
  }
}

const savedTags = loadSavedTags();

function hydrateTags() {
  data.forEach((item) => {
    if (savedTags[item.id]) {
      item.tags = savedTags[item.id];
    }
  });
}

function persistTags(id, tags) {
  savedTags[id] = tags;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(savedTags));
}

function withinRange(item) {
  if (state.datePicker) {
    return item.processedAt === state.datePicker;
  }
  if (state.dateRange === 'all') return true;
  const itemDate = new Date(item.processedAt + 'T00:00:00');
  const diff = (baseDate - itemDate) / (1000 * 60 * 60 * 24);
  if (state.dateRange === 'today') return diff === 0;
  return diff <= Number(state.dateRange);
}

function matchesSearch(item) {
  if (!state.search) return true;
  const haystack = [
    item.title,
    item.article.summary,
    ...item.topComments.map((c) => c.text)
  ].join(' ').toLowerCase();
  return haystack.includes(state.search.toLowerCase());
}

function matchesCategory(item) {
  if (state.categories.size === 0) return true;
  return item.categories.some((cat) => state.categories.has(cat));
}

function matchesCluster(item) {
  if (state.clusters.size === 0) return true;
  return state.clusters.has(item.cluster);
}

function matchesAdvanced(item) {
  const scoreMin = Number(state.scoreMin || 0);
  const commentsMin = Number(state.commentsMin || 0);
  if (scoreMin && item.score < scoreMin) return false;
  if (commentsMin && item.commentCount < commentsMin) return false;
  if (state.author && !item.author.toLowerCase().includes(state.author.toLowerCase())) return false;
  return true;
}

function getFiltered() {
  return data.filter((item) => (
    withinRange(item) &&
    matchesSearch(item) &&
    matchesCategory(item) &&
    matchesCluster(item) &&
    matchesAdvanced(item)
  ));
}

function renderCategoryPills() {
  const categories = Array.from(new Set(data.flatMap((item) => item.categories))).sort();
  elements.categoryPills.innerHTML = '';
  categories.forEach((category) => {
    const button = document.createElement('button');
    button.className = 'chip';
    button.textContent = category;
    if (state.categories.has(category)) button.classList.add('active');
    button.addEventListener('click', () => {
      if (state.categories.has(category)) {
        state.categories.delete(category);
      } else {
        state.categories.add(category);
      }
      renderCategoryPills();
      render();
    });
    elements.categoryPills.appendChild(button);
  });
}

function renderClusterPills() {
  const clusters = Array.from(new Set(data.map((item) => item.cluster))).sort();
  elements.clusterPills.innerHTML = '';
  clusters.forEach((cluster) => {
    const button = document.createElement('button');
    button.className = 'chip';
    button.textContent = cluster;
    if (state.clusters.has(cluster)) button.classList.add('active');
    button.addEventListener('click', () => {
      if (state.clusters.has(cluster)) {
        state.clusters.delete(cluster);
      } else {
        state.clusters.add(cluster);
      }
      renderClusterPills();
      render();
    });
    elements.clusterPills.appendChild(button);
  });
}

function renderClusterBar() {
  const clusters = Array.from(new Set(data.map((item) => item.cluster))).sort();
  elements.clusterBar.innerHTML = '';
  clusters.forEach((cluster) => {
    const button = document.createElement('button');
    button.className = 'chip';
    button.textContent = cluster;
    if (state.clusters.has(cluster)) button.classList.add('active');
    button.addEventListener('click', () => {
      if (state.clusters.has(cluster)) {
        state.clusters.delete(cluster);
      } else {
        state.clusters.add(cluster);
      }
      renderClusterPills();
      renderClusterBar();
      render();
    });
    elements.clusterBar.appendChild(button);
  });
}

function renderTagPills() {
  const tagCounts = new Map();
  data.forEach((item) => item.tags.forEach((tag) => tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1)));
  const sorted = Array.from(tagCounts.entries()).sort((a, b) => b[1] - a[1]).slice(0, 10);
  elements.tagPills.innerHTML = '';
  sorted.forEach(([tag]) => {
    const button = document.createElement('button');
    button.className = 'chip';
    button.textContent = tag;
    button.addEventListener('click', () => {
      elements.search.value = tag;
      state.search = tag;
      render();
    });
    elements.tagPills.appendChild(button);
  });
}

function renderCalendar() {
  const monthDate = new Date(state.calendarYear, state.calendarMonth, 1);
  const monthName = monthDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  elements.monthLabel.textContent = monthName;
  elements.calendarGrid.innerHTML = '';

  const startDay = monthDate.getDay();
  const daysInMonth = new Date(state.calendarYear, state.calendarMonth + 1, 0).getDate();
  const counts = countByDate();

  for (let i = 0; i < startDay; i += 1) {
    const empty = document.createElement('div');
    empty.className = 'calendar-day empty';
    elements.calendarGrid.appendChild(empty);
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    const date = new Date(state.calendarYear, state.calendarMonth, day);
    const key = toKey(date);
    const button = document.createElement('button');
    button.className = 'calendar-day';
    button.textContent = day;

    if (counts[key]) {
      button.classList.add('has-data');
    }
    if (key === toKey(baseDate)) {
      button.classList.add('today');
    }
    if (state.datePicker && key === state.datePicker) {
      button.classList.add('selected');
    }

    button.addEventListener('click', () => {
      if (!counts[key]) return;
      state.datePicker = key;
      state.dateRange = 'all';
      elements.datePicker.value = key;
      dateButtons.forEach((btn) => btn.classList.remove('active'));
      render();
      renderCalendar();
      renderTimeline();
    });

    elements.calendarGrid.appendChild(button);
  }
}

function countByDate() {
  return data.reduce((acc, item) => {
    acc[item.processedAt] = (acc[item.processedAt] || 0) + 1;
    return acc;
  }, {});
}

function renderTimeline() {
  const counts = countByDate();
  elements.timelineStrip.innerHTML = '';
  for (let offset = 0; offset < 14; offset += 1) {
    const date = new Date(baseDate);
    date.setDate(baseDate.getDate() - offset);
    const key = toKey(date);
    const button = document.createElement('button');
    button.className = 'timeline-day';
    button.innerHTML = `
      <strong>${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</strong>
      <span>${counts[key] || 0} threads</span>
    `;
    if (state.datePicker === key) {
      button.classList.add('active');
    }
    button.addEventListener('click', () => {
      if (!counts[key]) return;
      state.datePicker = key;
      state.dateRange = 'all';
      elements.datePicker.value = key;
      dateButtons.forEach((btn) => btn.classList.remove('active'));
      render();
      renderCalendar();
      renderTimeline();
    });
    elements.timelineStrip.appendChild(button);
  }
}

function renderCards(items) {
  elements.cards.innerHTML = '';
  if (!state.groupByCluster) {
    items.forEach((item) => {
      elements.cards.appendChild(buildCard(item));
    });
    return;
  }

  const grouped = items.reduce((acc, item) => {
    acc[item.cluster] = acc[item.cluster] || [];
    acc[item.cluster].push(item);
    return acc;
  }, {});

  Object.keys(grouped).sort().forEach((cluster) => {
    const group = document.createElement('div');
    group.className = 'cluster-group';
    group.innerHTML = `<h3>${cluster}</h3>`;
    const grid = document.createElement('div');
    grid.className = 'cards';
    grouped[cluster].forEach((item) => grid.appendChild(buildCard(item)));
    group.appendChild(grid);
    elements.cards.appendChild(group);
  });
}

function buildCard(item) {
  const card = document.createElement('article');
  card.className = 'card';
  card.innerHTML = `
      <h3 class="card-title">${item.title}</h3>
      <div class="card-meta">
        <span>${formatDate(item.processedAt)}</span>
        <span>⭐ ${item.score}</span>
        <span>💬 ${item.commentCount}</span>
        <span>${item.cluster}</span>
      </div>
      <p class="card-summary">${item.article.summary}</p>
      <div class="card-tags">
        ${item.categories.map((cat) => `<span>${cat}</span>`).join('')}
      </div>
    `;
  card.addEventListener('click', () => openDrawer(item.id));
  return card;
}

function renderList(items) {
  elements.listBody.innerHTML = '';
  items.forEach((item) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${item.title}</td>
      <td>${item.categories.join(', ')}</td>
      <td>${item.cluster}</td>
      <td>${item.score}</td>
      <td>${item.commentCount}</td>
      <td>${formatDate(item.processedAt)}</td>
    `;
    row.addEventListener('click', () => openDrawer(item.id));
    elements.listBody.appendChild(row);
  });
}

function updateHeader(count) {
  elements.resultCount.textContent = `${count} thread${count === 1 ? '' : 's'}`;
  if (state.datePicker) {
    elements.resultTitle.textContent = `Wisdom for ${formatDate(state.datePicker)}`;
  } else if (state.dateRange === 'today') {
    elements.resultTitle.textContent = 'Today’s wisdom';
  } else if (state.dateRange === '7') {
    elements.resultTitle.textContent = 'Last 7 days';
  } else if (state.dateRange === '30') {
    elements.resultTitle.textContent = 'Last 30 days';
  } else {
    elements.resultTitle.textContent = 'All wisdom';
  }
}

function render() {
  const items = getFiltered();
  updateHeader(items.length);
  renderCards(items);
  renderList(items);
  elements.cards.style.display = state.view === 'card' ? 'grid' : 'none';
  elements.list.style.display = state.view === 'list' ? 'table' : 'none';
  elements.clusterToggle.classList.toggle('active', state.groupByCluster);
}

function openDrawer(id) {
  const item = data.find((entry) => entry.id === id);
  if (!item) return;
  state.selectedId = id;
  elements.drawer.classList.add('open');
  elements.drawer.setAttribute('aria-hidden', 'false');
  elements.drawerTitle.textContent = item.title;
  elements.drawerMeta.innerHTML = `
    <span>By ${item.author}</span>
    <span>Processed ${formatDate(item.processedAt)}</span>
    <span>⭐ ${item.score} • 💬 ${item.commentCount}</span>
    <span>Cluster: ${item.cluster}</span>
  `;
  elements.drawerArticle.textContent = `${item.article.summary} (${item.article.readingTime} read)`;
  elements.drawerLink.href = item.article.url;
  elements.drawerComments.innerHTML = item.topComments
    .map((comment) => `<li>“${comment.text}” (${comment.score} pts)</li>`)
    .join('');
  renderDrawerTags(item.tags);
}

function renderDrawerTags(tags) {
  elements.drawerTags.innerHTML = '';
  tags.forEach((tag) => {
    const tagEl = document.createElement('span');
    tagEl.textContent = tag;
    elements.drawerTags.appendChild(tagEl);
  });
}

function addTagToSelected(tag) {
  if (!state.selectedId) return;
  const item = data.find((entry) => entry.id === state.selectedId);
  if (!item) return;
  const trimmed = tag.trim();
  if (!trimmed || item.tags.includes(trimmed)) return;
  item.tags.push(trimmed);
  persistTags(item.id, item.tags);
  renderDrawerTags(item.tags);
  renderTagPills();
}

function setBaseDate() {
  const dates = data.map((item) => new Date(item.processedAt + 'T00:00:00'));
  const maxDate = dates.reduce((max, date) => (date > max ? date : max), new Date(0));
  baseDate = maxDate > new Date() ? maxDate : new Date();
  state.calendarMonth = baseDate.getMonth();
  state.calendarYear = baseDate.getFullYear();
}

function exportJson(items) {
  const blob = new Blob([JSON.stringify(items, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  triggerDownload(url, `daily-wisdom-${Date.now()}.json`);
}

function exportCsv(items) {
  const headers = [
    'id', 'title', 'author', 'score', 'commentCount', 'processedAt',
    'categories', 'tags', 'cluster', 'articleUrl'
  ];
  const rows = items.map((item) => [
    item.id,
    escapeCsv(item.title),
    escapeCsv(item.author),
    item.score,
    item.commentCount,
    item.processedAt,
    escapeCsv(item.categories.join('|')),
    escapeCsv(item.tags.join('|')),
    escapeCsv(item.cluster),
    escapeCsv(item.article.url)
  ].join(','));
  const csv = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  triggerDownload(url, `daily-wisdom-${Date.now()}.csv`);
}

function escapeCsv(value) {
  const stringValue = String(value ?? '');
  if (/[",\n]/.test(stringValue)) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }
  return stringValue;
}

function triggerDownload(url, filename) {
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function wireEvents() {
  viewButtons.forEach((button) => {
    button.addEventListener('click', () => {
      viewButtons.forEach((btn) => btn.classList.remove('active'));
      button.classList.add('active');
      state.view = button.dataset.view;
      render();
    });
  });

  dateButtons.forEach((button) => {
    button.addEventListener('click', () => {
      dateButtons.forEach((btn) => btn.classList.remove('active'));
      button.classList.add('active');
      state.dateRange = button.dataset.range;
      state.datePicker = '';
      elements.datePicker.value = '';
      render();
      renderCalendar();
      renderTimeline();
    });
  });

  elements.clusterToggle.addEventListener('click', () => {
    state.groupByCluster = !state.groupByCluster;
    render();
  });

  elements.search.addEventListener('input', (event) => {
    state.search = event.target.value.trim();
    render();
  });

  elements.clearSearch.addEventListener('click', () => {
    state.search = '';
    elements.search.value = '';
    render();
  });

  elements.datePicker.addEventListener('change', (event) => {
    state.datePicker = event.target.value;
    dateButtons.forEach((btn) => btn.classList.remove('active'));
    render();
    renderCalendar();
    renderTimeline();
  });

  document.getElementById('closeDrawer').addEventListener('click', () => {
    elements.drawer.classList.remove('open');
    elements.drawer.setAttribute('aria-hidden', 'true');
  });

  elements.tagInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      addTagToSelected(event.target.value);
      event.target.value = '';
    }
  });

  elements.prevMonth.addEventListener('click', () => {
    state.calendarMonth -= 1;
    if (state.calendarMonth < 0) {
      state.calendarMonth = 11;
      state.calendarYear -= 1;
    }
    renderCalendar();
  });

  elements.nextMonth.addEventListener('click', () => {
    state.calendarMonth += 1;
    if (state.calendarMonth > 11) {
      state.calendarMonth = 0;
      state.calendarYear += 1;
    }
    renderCalendar();
  });

  elements.scoreMin.addEventListener('input', (event) => {
    state.scoreMin = event.target.value;
    render();
  });

  elements.commentsMin.addEventListener('input', (event) => {
    state.commentsMin = event.target.value;
    render();
  });

  elements.authorFilter.addEventListener('input', (event) => {
    state.author = event.target.value.trim();
    render();
  });

  elements.resetFilters.addEventListener('click', () => {
    state.scoreMin = '';
    state.commentsMin = '';
    state.author = '';
    elements.scoreMin.value = '';
    elements.commentsMin.value = '';
    elements.authorFilter.value = '';
    render();
  });

  elements.exportJson.addEventListener('click', () => {
    exportJson(getFiltered());
  });

  elements.exportCsv.addEventListener('click', () => {
    exportCsv(getFiltered());
  });
}

async function loadConfig() {
  try {
    const response = await fetch(`${CONFIG_SERVER}/api/config`);
    if (response.ok) {
      const config = await response.json();
      SUPABASE_URL = config.supabaseUrl || '';
      SUPABASE_ANON_KEY = config.supabaseAnonKey || '';
      console.log('Loaded Supabase config from server');
    }
  } catch (error) {
    console.warn('Config server unavailable, will use local data only:', error.message);
  }
}

async function loadData() {
  const useSupabase = SUPABASE_URL && SUPABASE_ANON_KEY;
  if (useSupabase) {
    try {
      const endpoint = `${SUPABASE_URL}/rest/v1/daily_wisdom_view?select=*`;
      const response = await fetch(endpoint, {
        headers: {
          apikey: SUPABASE_ANON_KEY,
          Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
          'Content-Type': 'application/json'
        }
      });
      if (!response.ok) {
        throw new Error('Failed to load Supabase data');
      }
      const json = await response.json();
      return Array.isArray(json) ? json : fallbackData;
    } catch (error) {
      console.warn('Supabase fetch failed, falling back to local data:', error.message);
      return fallbackData;
    }
  }

  try {
    const response = await fetch(DATA_URL, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error('Failed to load data');
    }
    const json = await response.json();
    return Array.isArray(json) ? json : fallbackData;
  } catch (error) {
    console.warn('Local data fetch failed, using fallback:', error.message);
    return fallbackData;
  }
}

async function init() {
  await loadConfig();
  data = await loadData();
  hydrateTags();
  setBaseDate();
  renderCategoryPills();
  renderClusterPills();
  renderClusterBar();
  renderTagPills();
  renderCalendar();
  renderTimeline();
  render();
}

wireEvents();
init();
