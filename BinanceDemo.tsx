import { type CSSProperties, type ReactNode, useEffect, useMemo, useRef, useState } from 'react'
import { Activity, BarChart3, Bell, Calculator, CheckCircle2, CircleDollarSign, ClipboardList, Crosshair, Gauge, History, LockKeyhole, Play, Radio, RefreshCw, Save, Send, Settings2, ShieldCheck, Target, TestTube2, TriangleAlert, UnlockKeyhole, Wallet, Zap } from 'lucide-react'
import { API_BASE } from './api'

const API = `${API_BASE}/binance-demo`
const V21_API = `${API_BASE}/v21`

type AnalysisPlan = {
  direction:'LONG'|'SHORT'|'BEKLE'
  entry:number
  stop_loss:number
  tp1:number
  tp2:number
  tp3:number
}

type AnalysisPlanPayload = Partial<AnalysisPlan> & {normalized_signal?:unknown;analysis?:unknown;plan?:unknown}

function normalizeAnalysisPlan(payload:unknown):AnalysisPlan|null {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return null
  const row = payload as AnalysisPlanPayload
  const nested = row.analysis && typeof row.analysis === 'object' && !Array.isArray(row.analysis)
    ? row.analysis as AnalysisPlanPayload
    : row.plan && typeof row.plan === 'object' && !Array.isArray(row.plan)
      ? row.plan as AnalysisPlanPayload
      : row
  const rawDirection = String(nested.direction || nested.normalized_signal || '').trim().toUpperCase()
  const direction = rawDirection === 'LONG' || rawDirection === 'BUY'
    ? 'LONG' : rawDirection === 'SHORT' || rawDirection === 'SELL' ? 'SHORT' : 'BEKLE'
  return {
    direction,
    entry:Number(nested.entry),
    stop_loss:Number(nested.stop_loss),
    tp1:Number(nested.tp1),
    tp2:Number(nested.tp2),
    tp3:Number(nested.tp3),
  }
}

type DemoStatus = {
  version:string
  mode:string
  configured:boolean
  connected:boolean
  armed:boolean
  armed_until:string|null
  rest_host:string
  websocket_host:string
  real_trading_locked:boolean
  limits:{max_margin_usdt:number;max_leverage:number;max_notional_usdt:number;max_open_positions:number;arm_minutes:number}
  last_checked:string|null
  last_error:string|null
  events:{kind:string;message:string;created_at:string}[]
  reconciliation?:{actual_exchange_open_positions:number;internal_active_plans:number;reconciled_active_positions:number;stale_positions_removed:number}
}

type DemoPosition = {
  symbol:string
  position_side?:'BOTH'|'LONG'|'SHORT'
  direction:'LONG'|'SHORT'
  quantity:number
  entry_price:number
  mark_price:number
  liquidation_price:number
  unrealized_pnl:number
  leverage:number|null
  margin_type:string|null
  requested_leverage?:number|null
  applied_leverage?:number|null
  leverage_verified?:boolean
  configuration_source?:string
}

type DemoOrder = {
  symbol:string
  order_id:number
  client_order_id:string
  side:string
  type:string
  status:string
  price:number
  quantity:number
  executed_quantity:number
  reduce_only:boolean
}

type DemoOrderResult = {
  symbol?:string
  order_id?:number
  client_order_id?:string
  status?:string
  type?:string
  side?:string
  quantity?:string
  price?:string|number
}

type DemoAlgoOrder = {
  symbol:string
  algo_id:number
  client_algo_id:string
  side:string
  type:string
  status:string
  trigger_price:number
  quantity:number
  close_position:boolean
}

type DemoPlan = {
  id:string
  symbol:string
  direction:'LONG'|'SHORT'
  order_type:string
  entry_price:string
  quantity:string
  margin_usdt:number
  leverage:number
  requested_leverage?:number
  applied_leverage?:number
  margin_type?:string
  leverage_verified?:boolean
  configuration_source?:string
  stop_loss:string
  targets:string[]
  status:string
  created_at:string
  monitoring_targets?:string[]
}

type DemoAccount = DemoStatus & {
  wallet_balance:number
  available_balance:number
  margin_balance:number
  unrealized_pnl:number
  positions:DemoPosition[]
  open_orders:DemoOrder[]
  open_algo_orders:DemoAlgoOrder[]
  hedge_mode:boolean
  plans:DemoPlan[]
  exchange_position_diagnostics?:{symbol:string;position_amount:string;exchange_actual_position:boolean}[]
}

type FormState = {
  direction:'LONG'|'SHORT'
  orderType:'MARKET'|'LIMIT'
  margin:string
  leverage:'1'|'2'
  limitPrice:string
  stop:string
  tp1:string
  tp2:string
  tp3:string
}

type V21Settings = {
  allowed_symbols:string[];allow_long:boolean;allow_short:boolean;max_loss_per_trade:number;max_margin_per_trade:number
  daily_loss_limit:number;daily_trade_limit:number;max_positions:number;min_confidence:number;max_volatility_pct:number
  max_correlation_pct:number;schedule_start_hour:number;schedule_end_hour:number;scan_seconds:number
  breakeven_enabled:boolean;breakeven_trigger_r:number;trailing_enabled:boolean;trailing_trigger_r:number
  trailing_distance_r:number;notifications:boolean;fee_bps_per_side:number;slippage_bps_per_side:number
}

type V21Journal = {id:string;created_at:string;kind:string;symbol?:string|null;status?:string|null;side?:string|null;price?:number|null;quantity?:number|null;realized_pnl?:number|null;reason?:string|null;message:string;source:string;reduce_only:boolean}
type V21Gate = {name:string;passed:boolean;value:string|number;target:string|number}
type V21Backtest = {symbol:string;interval:string;trades:number;wins:number;win_rate:number;net_pnl:number;ending_equity:number;max_drawdown_pct:number;profit_factor:number;no_lookahead:boolean;folds:{name:string;trades:number;net_pnl:number}[];recent_trades:{signal_time:number;entry_time:number;exit_time:number;direction:string;entry:number;exit:number;reason:string;pnl:number;cost_usdt:number;regime:string}[];note:string}
type V21Summary = {
  version:string;mode:string;settings:V21Settings
  auto:{enabled:boolean;busy:boolean;cycles:number;last_scan:string|null;last_decision:string;last_error:string|null;rejection_gate?:string|null;rejection_reason?:string|null}
  scanner:{active:boolean;scan_status:string;scan_interval_seconds:number;coins_scanned:number;selected_count:number;eligible_count:number;last_scan_at:string|null;next_scan_at:string|null;last_error:string|null;top_candidates:{rank:number;symbol:string;direction:string;score:number;confidence:string;confidence_value?:number;trend?:string;momentum?:string;volatility_pct?:number;reasons?:string[]}[];selected_symbols:string[];last_stage:string}
  stream:{status:string;transport:string;last_event:string|null;last_sync:string|null;reconnect_count:number;error_count:number;last_error:string|null}
  daily:{date:string;auto_entries:number;events:number;realized_pnl:number;remaining_loss_budget:number}
  account:{wallet_balance:number|null;available_balance:number|null;unrealized_pnl:number|null;positions:number;reconciled_active_positions?:number;normal_orders:number;algo_orders:number}
  protection:{repairs:number;duplicate_blocks:number};journal:V21Journal[];backtest:V21Backtest|null
  certificate:{version:string;status:string;score:number;passed_gates:number;total_gates:number;gates:V21Gate[];reason:string;generated_at:string}
  last_saved:string|null;real_trading_locked:boolean
}

type V21RiskPreview = {symbol:string;leverage:number;risk_pct:number;notional_usdt:number;margin_usdt:number;estimated_stop_loss_usdt:number;capped:boolean;quantity_preview:string;step_size:string}
type V21Performance = {period:string;total_trades:number;wins:number;losses:number;win_rate:number;total_profit:number;total_loss:number;net_profit:number;average_trade:number;best_trade:number;worst_trade:number;profit_factor:number;max_drawdown:number;demo_only:boolean;read_only:boolean}
type V21Tab = 'trade'|'risk'|'journal'|'auto'|'backtest'|'performance'|'certificate'

const initialForm:FormState = {
  direction:'LONG',orderType:'MARKET',margin:'50',leverage:'2',limitPrice:'',stop:'',tp1:'',tp2:'',tp3:'',
}

const fmt = (value?:number|null) => value === undefined || value === null || !Number.isFinite(value) ? '—' : value.toLocaleString('tr-TR',{maximumFractionDigits:value < 10 ? 5 : 2})
const stamp = (value?:string|null) => value ? new Date(value).toLocaleString('tr-TR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '—'
const numberValue = (value:string) => Number(value.replace(',','.'))
const gateLabel = (gate?:string|null) => ({DEMO_ARM:'Demo kilidi kapalı',MAX_POSITIONS:'Pozisyon limiti dolu',DAILY_TRADE_LIMIT:'Günlük işlem limiti dolu',DAILY_LOSS_LIMIT:'Günlük zarar limiti aktif',MARKET_HOURS:'Çalışma saatleri dışında',ALLOWED_SYMBOLS:'İzinli parite dışında',RISK_LEVELS:'Risk seviyeleri geçersiz',DEMO_EXECUTION:'Demo emir reddedildi'}[gate || ''] || 'Fırsat bekleniyor')

const fieldNames:Record<string,string> = {
  margin_usdt:'Marjin',leverage:'Kaldıraç',limit_price:'Limit fiyatı',stop_loss:'Stop Loss',
  tp1:'TP1',tp2:'TP2',tp3:'TP3',direction:'Yön',order_type:'Emir türü',symbol:'Parite',
}

function apiErrorMessage(detail:unknown):string {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const messages = detail.map(item => {
      if (!item || typeof item !== 'object') return String(item)
      const row = item as {loc?:unknown[];msg?:unknown}
      const field = Array.isArray(row.loc) ? String(row.loc.at(-1) ?? '') : ''
      if (field === 'margin_usdt') return 'Marjin 5–100 USDT arasında olmalı.'
      if (field === 'leverage') return 'Kaldıraç yalnızca 1x veya 2x olabilir.'
      if (['limit_price','stop_loss','tp1','tp2','tp3'].includes(field)) return `${fieldNames[field]} boş bırakılamaz ve 0’dan büyük olmalı.`
      const message = typeof row.msg === 'string' ? row.msg : 'Geçersiz değer'
      return `${fieldNames[field] || field || 'Alan'}: ${message}`
    }).filter(Boolean)
    if (messages.length) return [...new Set(messages)].join(' · ')
  }
  if (detail && typeof detail === 'object') {
    const message = (detail as {message?:unknown}).message
    if (typeof message === 'string') return message
  }
  return 'Binance Demo isteği doğrulanamadı. Emir alanlarını kontrol edin.'
}

async function apiCall<T>(path:string, options?:RequestInit):Promise<T> {
  const response = await fetch(`${API}${path}`, options)
  const payload:unknown = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(apiErrorMessage((payload as {detail?:unknown})?.detail))
  return payload as T
}

async function v21Call<T>(path:string, options?:RequestInit):Promise<T> {
  const response = await fetch(`${V21_API}${path}`, options)
  const payload:unknown = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(apiErrorMessage((payload as {detail?:unknown})?.detail))
  return payload as T
}

function PositionMap({position,plan}:{position:DemoPosition;plan?:DemoPlan}) {
  const entry = position.entry_price
  const mark = position.mark_price
  const stop = Number(plan?.stop_loss || 0)
  const targets = (plan?.targets || []).map(Number).filter(Number.isFinite)
  const rawLevels = [stop,entry,...targets,mark].filter(value => value > 0)
  const low = Math.min(...rawLevels)
  const high = Math.max(...rawLevels)
  const padding = Math.max((high-low)*.10,entry*.001)
  const min = low-padding
  const max = high+padding
  const left = (value:number) => `${Math.max(1,Math.min(99,(value-min)/Math.max(.000001,max-min)*100))}%`
  const grid = Array.from({length:9},(_,index) => min+(max-min)*(index+1)/10)
  return <div className="demoPositionMap">
    <div className="demoMapRail">{grid.map((level,index) => <i key={index} style={{left:left(level)}}/>)}
      {stop > 0 && <span className="demoMapPin demoStopPin" style={{left:left(stop)}}><b>STOP</b><em>{fmt(stop)}</em></span>}
      <span className="demoMapPin demoEntryPin" style={{left:left(entry)}}><b>GİRİŞ</b><em>{fmt(entry)}</em></span>
      {targets.map((target,index) => <span className="demoMapPin demoTargetPin" key={target} style={{left:left(target)}}><b>TP{index+1}</b><em>{fmt(target)}</em></span>)}
      <span className="demoMapMark" style={{left:left(mark)}}><i/><b>CANLI {fmt(mark)}</b></span>
    </div>
    <footer><span>SEVİYE IZGARASI</span><b>{position.direction} · {position.leverage ? `${position.leverage}x` : 'DOĞRULANIYOR'}</b><em>{plan?.status || 'Plan kaydı aranıyor'}</em></footer>
  </div>
}

export default function BinanceDemo({active,symbol,analysis,chart}:{active:boolean;symbol:string;analysis:AnalysisPlan|null;chart?:ReactNode}) {
  const [status,setStatus] = useState<DemoStatus|null>(null)
  const [account,setAccount] = useState<DemoAccount|null>(null)
  const [form,setForm] = useState<FormState>(initialForm)
  const [armText,setArmText] = useState('')
  const [busy,setBusy] = useState(false)
  const [message,setMessage] = useState('Önce bağlantıyı test edin; ardından analiz planını doğrulayın.')
  const [messageKind,setMessageKind] = useState<'info'|'ok'|'error'>('info')
  const [clock,setClock] = useState(Date.now())
  const [tab,setTab] = useState<V21Tab>('trade')
  const [v21,setV21] = useState<V21Summary|null>(null)
  const [settingsDraft,setSettingsDraft] = useState<V21Settings|null>(null)
  const [v21Busy,setV21Busy] = useState(false)
  const [riskLoss,setRiskLoss] = useState('5')
  const [riskPreview,setRiskPreview] = useState<V21RiskPreview|null>(null)
  const [performance,setPerformance] = useState<V21Performance|null>(null)
  const [performancePeriod,setPerformancePeriod] = useState<'all'|'daily'|'weekly'|'monthly'>('all')
  const [historyPayload,setHistoryPayload] = useState<{orders:Record<string,unknown>[];algo_orders:Record<string,unknown>[];trades:Record<string,unknown>[]} | null>(null)
  const [autoConfirm,setAutoConfirm] = useState('')
  const [backtestSymbol,setBacktestSymbol] = useState(symbol)
  const [lastOrder,setLastOrder] = useState<DemoOrderResult|null>(null)
  const demoDeckRef = useRef<HTMLElement>(null)
  const workspaceRef = useRef<HTMLElement>(null)
  const accountRefreshId = useRef(0)
  const initialScanRequested = useRef(false)
  const initialScanInFlight = useRef(false)
  const v21RequestId = useRef(0)
  const lastNotificationId = useRef<string|null>(null)

  const refreshStatus = async () => {
    try {
      const payload = await apiCall<DemoStatus>('/status')
      setStatus(payload)
      if (!payload.configured) setAccount(null)
      return payload
    } catch { setStatus(null); return null }
  }
  const refreshAccount = async (quiet=true) => {
    const requestId = ++accountRefreshId.current
    try {
      const payload = await apiCall<DemoAccount>('/account')
      if (requestId !== accountRefreshId.current) return
      setAccount(payload); setStatus(payload)
    } catch (error) {
      if (requestId !== accountRefreshId.current) return
      setAccount(null)
      if (!quiet) { setMessage(error instanceof Error ? error.message : 'Demo hesap okunamadı.'); setMessageKind('error') }
    }
  }
  const refreshV21 = async (quiet=true) => {
    const requestId = ++v21RequestId.current
    try {
      const payload = await v21Call<V21Summary>('/summary')
      if (requestId !== v21RequestId.current) return null
      setV21(payload)
      setSettingsDraft(current => current || payload.settings)
      return payload
    } catch (error) {
      if (!quiet) { setMessage(error instanceof Error ? error.message : 'V21 merkezi okunamadı.');setMessageKind('error') }
      return null
    }
  }
  const refreshPerformance = async (period=performancePeriod) => {
    try { setPerformance(await v21Call<V21Performance>(`/performance?period=${period}`)) }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Performans verisi alınamadı.');setMessageKind('error') }
  }

  const requestScannerScan = async () => {
    if (initialScanInFlight.current) return
    initialScanInFlight.current = true
    try {
      await v21Call('/scanner/scan',{method:'POST'})
      initialScanRequested.current = true
      await refreshV21(true)
    } catch (error) {
      if (!initialScanRequested.current) setMessage(error instanceof Error ? error.message : 'İlk scanner taraması başlatılamadı.')
    } finally { initialScanInFlight.current = false }
  }

  useEffect(() => {
    if (!active) return
    let mounted = true
    const refresh = async () => {
      const payload = await refreshStatus()
      if (mounted && payload?.configured) await refreshAccount(true)
      if (mounted) {
        const summary = await refreshV21(true)
        if (summary?.scanner && !summary.scanner.last_scan_at && !initialScanRequested.current) void requestScannerScan()
      }
    }
    refresh()
    const timer = window.setInterval(refresh,10000)
    const ticker = window.setInterval(() => setClock(Date.now()),1000)
    return () => { mounted=false;window.clearInterval(timer);window.clearInterval(ticker) }
  },[active])

  useEffect(() => {
    if (!active || !v21?.scanner.next_scan_at) return
    const delay = Math.max(0, new Date(v21.scanner.next_scan_at).getTime() - Date.now()) + 1000
    const timer = window.setTimeout(() => void requestScannerScan(), delay)
    return () => window.clearTimeout(timer)
  },[active,v21?.scanner.next_scan_at])

  useEffect(() => {
    const openCertificate = () => setTab('certificate')
    window.addEventListener('protrebot-open-demo-certificate',openCertificate)
    return () => window.removeEventListener('protrebot-open-demo-certificate',openCertificate)
  },[])

  useEffect(() => { setBacktestSymbol(symbol) },[symbol])

  useEffect(() => {
    const newest = v21?.journal?.[0]
    if (!newest) return
    if (lastNotificationId.current === null) { lastNotificationId.current = newest.id;return }
    if (newest.id === lastNotificationId.current) return
    lastNotificationId.current = newest.id
    if (v21?.settings.notifications && 'Notification' in window && Notification.permission === 'granted') {
      new Notification(`ProTreBot · ${newest.kind}`, {body:newest.message,tag:newest.id})
    }
  },[v21?.journal?.[0]?.id])

  useEffect(() => { if (active && tab === 'performance') void refreshPerformance() },[active,tab,performancePeriod])

  useEffect(() => {
    const target = tab === 'trade' ? demoDeckRef.current : workspaceRef.current
    if (!target) return
    window.requestAnimationFrame(() => target.scrollIntoView({block:'start',behavior:'smooth'}))
  },[tab])

  const armSeconds = status?.armed_until ? Math.max(0,Math.floor((new Date(status.armed_until).getTime()-clock)/1000)) : 0
  const nextScanMs = v21?.scanner.next_scan_at ? new Date(v21.scanner.next_scan_at).getTime() : null
  const nextScanSeconds = nextScanMs === null ? null : Math.max(0,Math.ceil((nextScanMs - clock) / 1000))
  const nextScanCountdown = nextScanSeconds === null ? '—' : `${Math.floor(nextScanSeconds / 60)} dk ${nextScanSeconds % 60} sn sonra`
  const activePlanBySymbol = useMemo(() => {
    const map = new Map<string,DemoPlan>()
    for (const plan of account?.plans || []) if (!['KAPANDI','İPTAL'].includes(plan.status)) map.set(plan.symbol,plan)
    return map
  },[account?.plans])

  const fillFromAnalysis = async () => {
    setBusy(true);setMessageKind('info');setMessage('Güncel analiz planı alınıyor…')
    try {
      let plan = normalizeAnalysisPlan(analysis)
      if (!plan || plan.direction === 'BEKLE') {
        const response = await fetch(`${API_BASE}/analysis/${symbol}?interval=15m`)
        const payload = await response.json().catch(() => null) as unknown
        if (!response.ok) throw new Error(apiErrorMessage(payload && typeof payload === 'object' && 'detail' in payload ? payload.detail : payload))
        plan = normalizeAnalysisPlan(payload)
      }
      if (!plan || !['LONG','SHORT'].includes(plan.direction)) throw new Error('Yön belirlenemedi; mevcut yön korunuyor.')
      const levels = [plan.entry,plan.stop_loss,plan.tp1,plan.tp2,plan.tp3]
      if (levels.some(value => !Number.isFinite(value) || value <= 0)) throw new Error('Analiz planında geçerli giriş, Stop ve TP seviyeleri bulunamadı.')
      const ordered = plan.direction === 'LONG'
        ? plan.stop_loss < plan.entry && plan.entry < plan.tp1 && plan.tp1 < plan.tp2 && plan.tp2 < plan.tp3
        : plan.stop_loss > plan.entry && plan.entry > plan.tp1 && plan.tp1 > plan.tp2 && plan.tp2 > plan.tp3
      if (!ordered) throw new Error(`${plan.direction} analizinde Stop, giriş ve TP seviyeleri yanlış sırada.`)
      const direction: 'LONG'|'SHORT' = plan.direction
      setForm(current => ({...current,direction,limitPrice:String(plan.entry),stop:String(plan.stop_loss),tp1:String(plan.tp1),tp2:String(plan.tp2),tp3:String(plan.tp3)}))
      setMessage('Giriş, Stop ve TP1–TP3 güncel analizden dolduruldu. Göndermeden önce mutlaka kontrol edin.');setMessageKind('ok')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Güncel analiz planı alınamadı.');setMessageKind('error')
    } finally {setBusy(false)}
  }

  const payload = () => {
    const margin = numberValue(form.margin)
    const leverage = Number(form.leverage)
    if (!Number.isFinite(margin) || margin < 5 || margin > 100) throw new Error('Demo marjini 5–100 USDT arasında olmalı.')
    if (![1,2].includes(leverage)) throw new Error('Kaldıraç yalnızca 1x veya 2x olabilir.')
    const levels = {stop_loss:numberValue(form.stop),tp1:numberValue(form.tp1),tp2:numberValue(form.tp2),tp3:numberValue(form.tp3)}
    const missing = Object.entries(levels).filter(([,value]) => !Number.isFinite(value) || value <= 0).map(([key]) => fieldNames[key])
    if (missing.length) throw new Error(`${missing.join(', ')} alanlarını güncel analizden doldurun veya elle geçerli fiyat girin.`)
    const limitPrice = numberValue(form.limitPrice)
    if (form.orderType === 'LIMIT' && (!Number.isFinite(limitPrice) || limitPrice <= 0)) throw new Error('Limit emrinde geçerli bir Limit fiyatı girmelisiniz.')
    return {
      symbol,direction:form.direction,order_type:form.orderType,margin_usdt:margin,leverage,
      limit_price:form.orderType === 'LIMIT' ? limitPrice : null,...levels,
    }
  }

  const changeMargin = (value:string) => {
    if (value === '') { setForm({...form,margin:value});return }
    const parsed = numberValue(value)
    if (Number.isFinite(parsed) && parsed <= 100) setForm({...form,margin:value})
  }

  const normalizeMargin = () => {
    const parsed = numberValue(form.margin)
    const safe = Number.isFinite(parsed) ? Math.min(100,Math.max(5,Math.round(parsed))) : 10
    setForm({...form,margin:String(safe)})
  }

  const runAction = async (action:() => Promise<unknown>,success:string) => {
    setBusy(true);setMessageKind('info');setMessage('İşlem Binance Futures Demo üzerinde doğrulanıyor…')
    try { await action();setMessage(success);setMessageKind('ok');await refreshStatus();await refreshAccount(true) }
    catch (error) { setMessage(error instanceof Error ? error.message : 'İşlem tamamlanamadı.');setMessageKind('error') }
    finally { setBusy(false) }
  }

  const connect = () => runAction(() => apiCall('/connect',{method:'POST'}),'Bağlantı başarılı: Sanal Futures Demo hesabı okunuyor; gerçek hesap kilitli.')
  const arm = () => runAction(() => apiCall('/arm',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmation:armText})}),'Demo emir kilidi 10 dakika için açıldı.')
  const disarm = () => runAction(() => apiCall('/disarm',{method:'POST'}),'Yeni Demo giriş emirleri kilitlendi; mevcut korumalar açık kalır.')
  const testOrder = () => runAction(() => apiCall('/order/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload())}),'Emir testi geçti; hiçbir emir veya pozisyon oluşturulmadı.')
  const submitOrder = () => {
    const confirmation = window.prompt('Demo emrini açmak için DEMO yazın:') || ''
    if (!confirmation.trim()) return
    return runAction(async () => {
      const result = await apiCall<{order?:DemoOrderResult}>('/order',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...payload(),confirmation:confirmation.trim()})})
      setLastOrder(result.order || null)
      return result
    },'Emir yalnızca Binance Futures Demo hesabına gönderildi; koruma durumu yenileniyor.')
  }
  const cancelOrder = (order:DemoOrder) => runAction(() => apiCall('/order/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symbol:order.symbol,order_id:order.order_id})}),`${order.symbol} Demo emri iptal edildi.`)
  const cancelAlgo = (order:DemoAlgoOrder) => runAction(() => apiCall('/algo/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symbol:order.symbol,algo_id:order.algo_id})}),`${order.symbol} koşullu Demo emri iptal edildi.`)
  const closePosition = (position:DemoPosition) => {
    const confirmation = window.prompt(`${position.symbol} Demo pozisyonunu kapatmak için DEMO KAPAT yazın:`) || ''
    if (!confirmation) return
    runAction(() => apiCall('/position/close',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symbol:position.symbol,position_side:position.position_side || 'BOTH',confirmation})}),`${position.symbol} için reduce-only Demo kapatma emri gönderildi.`)
  }
  const emergency = () => {
    const confirmation = window.prompt('Bot emirlerini iptal edip tüm Demo pozisyonlarını kapatmak için DEMO ACİL DURDUR yazın:') || ''
    if (!confirmation) return
    runAction(() => apiCall('/emergency',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmation,close_positions:true})}),'Acil Demo durdurma tamamlandı; giriş kilidi kapandı.')
  }

  const runV21 = async (action:() => Promise<V21Summary|unknown>,success:string) => {
    setV21Busy(true);setMessageKind('info');setMessage('V21 Demo güvenlik kapıları doğrulanıyor…')
    try {
      const result = await action()
      if (result && typeof result === 'object' && 'settings' in result) {
        const summary = result as V21Summary;setV21(summary);setSettingsDraft(summary.settings)
      } else await refreshV21(true)
      setMessage(success);setMessageKind('ok')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'V21 işlemi tamamlanamadı.');setMessageKind('error') }
    finally { setV21Busy(false) }
  }

  const saveSettings = () => {
    if (!settingsDraft) return
    runV21(() => v21Call<V21Summary>('/settings',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(settingsDraft)}),'Risk, yön ve otomasyon sınırları yerel V21 kasasına kaydedildi.')
  }
  const calculateRisk = () => {
    if (!analysis || analysis.entry <= 0 || analysis.stop_loss <= 0) { setMessage('Önce seçili paritenin analiz planını bekleyin.');setMessageKind('error');return }
    setV21Busy(true)
    v21Call<V21RiskPreview>('/risk/size',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symbol,entry:analysis.entry,stop:analysis.stop_loss,max_loss_usdt:numberValue(riskLoss),leverage:2})})
      .then(payload => {setRiskPreview(payload);setMessage('Maksimum kayba göre Demo pozisyon boyutu hesaplandı.');setMessageKind('ok')})
      .catch(error => {setMessage(error instanceof Error ? error.message : 'Risk hesabı yapılamadı.');setMessageKind('error')})
      .finally(() => setV21Busy(false))
  }
  const toggleAuto = () => {
    if (v21?.auto.enabled) runV21(() => v21Call<V21Summary>('/auto/stop',{method:'POST'}),'Yeni otomatik Demo girişleri durduruldu; mevcut korumalar açık.')
    else runV21(() => v21Call<V21Summary>('/auto/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmation:autoConfirm})}),'Kontrollü V21 Demo otomasyonu başlatıldı.')
  }
  const runSmokeTest = () => runV21(
    () => v21Call('/smoke-test',{method:'POST'}),
    'Demo smoke işlemi açıldı; paper pozisyonu dashboard’a yazıldı.',
  )
  const runBacktest = () => runV21(
    async () => { const result = await v21Call<V21Backtest>('/backtest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({symbol:backtestSymbol,interval:'15m',limit:1000})});await refreshV21(true);return result },
    `${backtestSymbol} kronolojik backtest tamamlandı; ücret ve kayma düşüldü.`,
  )
  const loadHistory = () => {
    setV21Busy(true)
    v21Call<{orders:Record<string,unknown>[];algo_orders:Record<string,unknown>[];trades:Record<string,unknown>[]}>(`/history/${symbol}`)
      .then(payload => {setHistoryPayload(payload);setMessage(`${symbol} Demo emir ve dolum geçmişi getirildi.`);setMessageKind('ok')})
      .catch(error => {setMessage(error instanceof Error ? error.message : 'Demo geçmişi alınamadı.');setMessageKind('error')})
      .finally(() => setV21Busy(false))
  }
  const runDrill = (kind:'RECONNECT'|'EMERGENCY'|'PROTECTION') => runV21(
    () => v21Call('/drill',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind})}),
    `${kind} tatbikatı tamamlandı; hiçbir gerçek emir gönderilmedi.`,
  )
  const enableNotifications = async () => {
    if (!('Notification' in window)) { setMessage('Bu tarayıcı masaüstü bildirimini desteklemiyor.');setMessageKind('error');return }
    const permission = await Notification.requestPermission()
    setMessage(permission === 'granted' ? 'Masaüstü Demo bildirimleri açıldı.' : 'Bildirim izni verilmedi.');setMessageKind(permission === 'granted' ? 'ok' : 'error')
  }

  const overviewWallet = account?.wallet_balance ?? v21?.account.wallet_balance
  const overviewAvailable = account?.available_balance ?? v21?.account.available_balance
  const overviewPnl = account?.unrealized_pnl ?? v21?.account.unrealized_pnl ?? v21?.daily.realized_pnl
  const overviewUsedMargin = account ? Math.max(0,account.wallet_balance - account.available_balance) : null
  const overviewMarginUsage = overviewWallet && overviewUsedMargin !== null ? overviewUsedMargin / overviewWallet * 100 : null
  const riskPosition = account?.positions?.[0]
  const riskDistance = riskPosition && riskPosition.entry_price > 0 ? Math.abs(riskPosition.mark_price - riskPosition.liquidation_price) / riskPosition.entry_price * 100 : null
  const riskLevel = riskDistance === null ? null : riskDistance < 2 ? 'HIGH RISK' : riskDistance < 5 ? 'MEDIUM RISK' : 'LOW RISK'
  const riskClass = riskLevel === null ? 'unavailable' : riskLevel === 'HIGH RISK' ? 'critical' : riskLevel === 'MEDIUM RISK' ? 'warning' : 'healthy'
  const activityItems = v21?.journal?.length ? v21.journal.slice(0,5).map(item => ({title:item.kind,description:item.message,meta:item.symbol || item.source,time:item.created_at})) : status?.events?.slice(0,5).map(item => ({title:item.kind,description:item.message,meta:'DEMO',time:item.created_at})) || []
  const qualityCandidate = v21?.scanner.top_candidates?.[0]
  const qualityScore = qualityCandidate?.score ?? null
  const qualityLabel = qualityScore === null ? null : qualityScore >= 80 ? 'STRONG' : qualityScore >= 60 ? 'GOOD' : qualityScore >= 40 ? 'MODERATE' : 'WEAK'
  const historyItems = v21?.backtest?.recent_trades?.slice(0,5) || []
  const safetyChecks = [
    {label:'Stop Loss',status:form.stop || analysis?.stop_loss ? 'PASS' : 'UNAVAILABLE',detail:form.stop || analysis?.stop_loss ? 'Protection level is present.' : 'No stop value is available.'},
    {label:'Risk value',status:riskPreview ? 'PASS' : analysis?.entry && analysis.stop_loss ? 'WARNING' : 'UNAVAILABLE',detail:riskPreview ? `${fmt(riskPreview.estimated_stop_loss_usdt)} USDT preview.` : analysis?.entry && analysis.stop_loss ? 'Risk preview requires review.' : 'Risk cannot be calculated yet.'},
    {label:'Risk / Reward',status:analysis && analysis.entry > 0 && analysis.stop_loss > 0 && analysis.tp1 > 0 ? (Math.abs(analysis.tp1 - analysis.entry) / Math.abs(analysis.entry - analysis.stop_loss) >= 1.5 ? 'PASS' : 'WARNING') : 'UNAVAILABLE',detail:analysis && analysis.entry > 0 && analysis.stop_loss > 0 && analysis.tp1 > 0 ? `${(Math.abs(analysis.tp1 - analysis.entry) / Math.abs(analysis.entry - analysis.stop_loss)).toFixed(2)}R derived from setup.` : 'R:R is unavailable.'},
    {label:'Daily risk limit',status:v21?.daily.remaining_loss_budget !== undefined ? (v21.daily.remaining_loss_budget > 0 ? 'PASS' : 'BLOCKED') : 'UNAVAILABLE',detail:v21?.daily.remaining_loss_budget !== undefined ? `${fmt(v21.daily.remaining_loss_budget)} USDT remaining.` : 'Daily risk data unavailable.'},
    {label:'Position exposure',status:account && v21?.settings.max_positions ? (account.positions.length < v21.settings.max_positions ? 'PASS' : 'WARNING') : 'UNAVAILABLE',detail:account && v21?.settings.max_positions ? `${account.positions.length}/${v21.settings.max_positions} positions.` : 'Exposure limit unavailable.'},
  ]
  const safetySummary = safetyChecks.some(check => check.status === 'BLOCKED') ? 'REVIEW WARNING' : safetyChecks.every(check => check.status === 'UNAVAILABLE') ? 'SAFETY CHECK UNAVAILABLE' : safetyChecks.some(check => check.status === 'WARNING') ? 'REVIEW WARNING' : 'SAFE TO REVIEW'
  const scoreFactors = [
    {label:'Trend alignment',value:qualityCandidate?.trend || analysis?.direction || 'Unavailable',points:qualityCandidate?.trend ? 25 : analysis?.direction ? 15 : null},
    {label:'Signal confirmation',value:analysis?.direction || 'Unavailable',points:analysis?.direction && analysis.direction !== 'BEKLE' ? 25 : null},
    {label:'Risk / Reward quality',value:analysis && analysis.entry > 0 && analysis.stop_loss > 0 && analysis.tp1 > 0 ? 'Calculated' : 'Unavailable',points:analysis && analysis.entry > 0 && analysis.stop_loss > 0 && analysis.tp1 > 0 ? Math.min(25,Math.round(Math.max(0,(Math.abs(analysis.tp1 - analysis.entry) / Math.abs(analysis.entry - analysis.stop_loss)) * 10))) : null},
    {label:'Market confidence',value:qualityCandidate?.confidence || 'Unavailable',points:qualityCandidate?.confidence_value !== undefined ? Math.round(Math.min(25,qualityCandidate.confidence_value / 4)) : null},
  ]
  const setupScorePoints = scoreFactors.reduce((total,factor) => total + (factor.points ?? 0),0)
  const setupScore = scoreFactors.some(factor => factor.points !== null) ? Math.round(setupScorePoints / scoreFactors.filter(factor => factor.points !== null).length * scoreFactors.length) : null
  const setupRating = setupScore === null ? 'Unrated / Insufficient Data' : setupScore >= 90 ? 'A+' : setupScore >= 80 ? 'A' : setupScore >= 65 ? 'B' : 'C'
  const coachTrades = v21?.journal?.filter(item => item.realized_pnl !== null && item.realized_pnl !== undefined) || []
  const coachBest = coachTrades.length ? Math.max(...coachTrades.map(item => item.realized_pnl as number)) : null
  const coachWorst = coachTrades.length ? Math.min(...coachTrades.map(item => item.realized_pnl as number)) : null
  const positionAssistant = account?.positions.map(position => {
    const plan = activePlanBySymbol.get(position.symbol)
    const stop = Number(plan?.stop_loss || 0)
    const target = Number(plan?.targets?.[0] || 0)
    const entry = position.entry_price
    const current = position.mark_price
    const entryDistance = entry > 0 ? Math.abs(current - entry) / entry * 100 : null
    const stopDistance = stop > 0 ? Math.abs(current - stop) / current * 100 : null
    const targetDistance = target > 0 ? Math.abs(target - current) / current * 100 : null
    const favorable = position.direction === 'LONG' ? current >= entry : current <= entry
    const stage = !entry || !current ? 'INSUFFICIENT POSITION DATA' : targetDistance !== null && targetDistance <= 1 ? 'TARGET APPROACH' : entryDistance !== null && entryDistance <= 1 ? 'ENTRY ZONE' : favorable ? 'PROFIT ZONE' : stop > 0 ? 'PROTECTION ZONE' : 'REVIEW REQUIRED'
    const observation = !stop ? 'Protection observation: stop data unavailable.' : targetDistance !== null && targetDistance <= 1 ? 'Target observation: price is near the first target.' : !favorable ? 'Review: price is adverse to the position direction.' : entryDistance !== null && entryDistance <= 1 ? 'Monitor: position is near break-even.' : 'Position status: monitor current price and protection.'
    const rr = stop > 0 && target > 0 && entry > 0 ? Math.abs(target - entry) / Math.abs(entry - stop) : null
    return {position,stop,target,entryDistance,stopDistance,targetDistance,stage,observation,rr}
  }) || []
  const analyticsTrades = coachTrades
  const analyticsWins = analyticsTrades.filter(trade => (trade.realized_pnl ?? 0) > 0)
  const analyticsLosses = analyticsTrades.filter(trade => (trade.realized_pnl ?? 0) < 0)
  const analyticsProfit = analyticsWins.reduce((total,trade) => total + (trade.realized_pnl ?? 0),0)
  const analyticsLoss = analyticsLosses.reduce((total,trade) => total + (trade.realized_pnl ?? 0),0)
  const analyticsTotal = analyticsTrades.length ? analyticsTrades.reduce((total,trade) => total + (trade.realized_pnl ?? 0),0) : performance?.net_profit ?? null
  const analyticsCount = analyticsTrades.length || performance?.total_trades || null
  const analyticsWinRate = analyticsTrades.length ? analyticsWins.length / analyticsTrades.length * 100 : performance?.win_rate ?? null
  const analyticsAverageWin = analyticsWins.length ? analyticsProfit / analyticsWins.length : null
  const analyticsAverageLoss = analyticsLosses.length ? analyticsLoss / analyticsLosses.length : null
  const analyticsProfitFactor = analyticsLoss < 0 ? analyticsProfit / Math.abs(analyticsLoss) : null
  const analyticsExpectancy = analyticsTrades.length && analyticsTotal !== null ? analyticsTotal / analyticsTrades.length : performance?.average_trade ?? null
  const setupAvailable = Boolean(qualityCandidate || analysis?.direction)
  const riskAvailable = Boolean(riskPreview || (analysis && v21?.daily.remaining_loss_budget !== undefined))
  const liveTradeAvailable = Boolean(account?.positions.length)
  const reviewAvailable = Boolean(performance || v21?.journal.length || v21?.backtest?.recent_trades.length)
  const workflowSteps = [
    {label:'Discover',target:'auto' as V21Tab,status:v21?.scanner.last_scan_at ? 'completed' : 'available'},
    {label:'Analyze',target:'trade' as V21Tab,status:setupAvailable ? 'completed' : 'unavailable'},
    {label:'Setup',target:'trade' as V21Tab,status:setupAvailable ? 'available' : 'unavailable'},
    {label:'Risk Check',target:'risk' as V21Tab,status:riskAvailable ? 'completed' : setupAvailable ? 'available' : 'unavailable'},
    {label:'Execute',target:'trade' as V21Tab,status:liveTradeAvailable ? 'completed' : riskAvailable ? 'available' : 'unavailable'},
    {label:'Review',target:'performance' as V21Tab,status:reviewAvailable ? 'available' : 'unavailable'},
  ]
  const workflowCurrentIndex = tab === 'auto' ? 0 : tab === 'risk' ? 3 : tab === 'performance' || tab === 'journal' ? 5 : 2
  const nextAction = liveTradeAvailable ? {label:'Monitor Live Trade',target:'journal' as V21Tab,detail:'Open position data is available in the live journal.'} : reviewAvailable ? {label:'Review Performance',target:'performance' as V21Tab,detail:'Recent journal or performance data is available for review.'} : !setupAvailable ? {label:'Review Market Scanner',target:'auto' as V21Tab,detail:'No live setup is available yet.'} : !riskAvailable ? {label:'Run Risk Check',target:'risk' as V21Tab,detail:'A live setup is available and requires risk review.'} : {label:'Open Trade Desk',target:'trade' as V21Tab,detail:'Risk context is available; review the trade desk before execution.'}
  const decisionCandidate = qualityCandidate
  const decisionRisk = riskPosition ? riskDistance !== null && riskDistance < 2 ? 'High' : riskDistance !== null && riskDistance < 5 ? 'Moderate' : 'Low' : null
  const decisionChecks = [
    {label:'Trend alignment',value:decisionCandidate?.trend || 'Unavailable'},
    {label:'Volume confirmation',value:'Unavailable'},
    {label:'Momentum confirmation',value:decisionCandidate?.momentum || 'Unavailable'},
    {label:'Market volatility',value:decisionCandidate?.volatility_pct !== undefined ? `%${fmt(decisionCandidate.volatility_pct)}` : 'Unavailable'},
    {label:'Risk status',value:decisionRisk || 'Unavailable'},
    {label:'Risk / reward',value:analysis && analysis.entry > 0 && analysis.stop_loss > 0 && analysis.tp1 > 0 ? `${(Math.abs(analysis.tp1 - analysis.entry) / Math.abs(analysis.entry - analysis.stop_loss)).toFixed(2)}R` : 'Unavailable'},
  ]
  const decisionLabel = !decisionCandidate && !analysis ? 'Unavailable' : decisionRisk === 'High' ? 'Needs Review' : riskAvailable ? 'Validated' : 'Needs Review'
  const whyTrade = decisionCandidate?.trend ? `Trend alignment is available from the scanner: ${decisionCandidate.trend}.` : analysis?.direction ? `Analysis provides a ${analysis.direction} direction; scanner trend confirmation is unavailable.` : 'No structured setup explanation is available yet.'
  const lifecycleEvents = v21?.journal?.filter(item => item.symbol === symbol || !item.symbol).slice(0,6) || []
  const replayTrade = historyItems[0]
  const replayEvents = replayTrade ? [{label:'Entry',time:replayTrade.entry_time,detail:fmt(replayTrade.entry)},{label:'Close',time:replayTrade.exit_time,detail:fmt(replayTrade.exit)}] : []

  return <section ref={demoDeckRef} className="binanceDemoDeck" aria-label="Binance Futures Demo Köprüsü" data-build-marker="BUILD_COMMIT" data-build-commit={import.meta.env.VITE_BUILD_COMMIT} data-position-source="reconciled_active_positions" data-diagnostics="exchange_position_diagnostics">
    <section className="demoHero">
      <div className="demoHeroCopy"><span>V21 · DEMO COMPLETE · TEK PAKET</span><h2>Binance Futures Demo Komuta Merkezi</h2><p>İşlem masası, risk kasası, canlı günlük, kontrollü otomasyon, kanıtlı backtest ve Demo sertifikası ayrı sekmelerde.</p><div><b><ShieldCheck/> DEMO ONLY</b><span>{status?.rest_host || 'https://demo-fapi.binance.com'}</span></div></div>
      <div className="demoHeroStatus">
        <span className={status?.configured ? 'demoOk' : 'demoWait'}><LockKeyhole/><small>ANAHTAR</small><b>{status?.configured ? 'YERELDE HAZIR' : 'AYAR BEKLİYOR'}</b></span>
        <span className={status?.connected ? 'demoOk' : 'demoWait'}><Radio/><small>DEMO API</small><b>{status?.connected ? 'BAĞLI' : 'BAĞLI DEĞİL'}</b></span>
        <span className={status?.armed ? 'demoArmed' : 'demoSafe'}>{status?.armed ? <UnlockKeyhole/> : <LockKeyhole/>}<small>EMİR KİLİDİ</small><b>{status?.armed ? `${Math.floor(armSeconds/60)}:${String(armSeconds%60).padStart(2,'0')}` : 'KAPALI'}</b></span>
      </div>
    </section>

    <nav className="v21Tabs" aria-label="V21 çalışma alanları">
      <button className={tab === 'trade' ? 'active' : ''} onClick={() => setTab('trade')}><Crosshair/><span><b>İŞLEM MASASI</b><small>Emir · Grafik · Pozisyon</small></span></button>
      <button className={tab === 'risk' ? 'active' : ''} onClick={() => setTab('risk')}><Gauge/><span><b>RİSK KASASI</b><small>Limit · Boyut · Stop</small></span></button>
      <button className={tab === 'journal' ? 'active' : ''} onClick={() => setTab('journal')}><ClipboardList/><span><b>CANLI GÜNLÜK</b><small>Dolum · Kapanış · Neden</small></span></button>
      <button className={tab === 'auto' ? 'active' : ''} onClick={() => setTab('auto')}><Zap/><span><b>OTOMASYON</b><small>İzin listesi · Kapılar</small></span></button>
      <button className={tab === 'backtest' ? 'active' : ''} onClick={() => setTab('backtest')}><BarChart3/><span><b>BACKTEST LAB</b><small>Ücret · Kayma · 3 dönem</small></span></button>
      <button className={tab === 'performance' ? 'active' : ''} onClick={() => setTab('performance')}><BarChart3/><span><b>PERFORMANS</b><small>PnL · Win rate · Drawdown</small></span></button><button className={tab === 'certificate' ? 'active' : ''} onClick={() => setTab('certificate')}><ShieldCheck/><span><b>SERTİFİKA</b><small>Sağlık · Tatbikat · Kanıt</small></span></button>
    </nav>

    <section className="v21Pulse">
      <span><i className={v21?.stream.status === 'CANLI' ? 'on' : ''}/><small>AKIŞ</small><b>{v21?.stream.status || 'BEKLENİYOR'}</b></span>
      <span><small>OTOMASYON</small><b>{v21?.auto.enabled ? 'ÇALIŞIYOR' : 'KAPALI'}</b></span>
      <span><small>GÜNLÜK DEMO</small><b>{v21?.daily.auto_entries ?? 0} / {v21?.settings.daily_trade_limit ?? 6}</b></span>
      <span><small>RİSK BÜTÇESİ</small><b>{fmt(v21?.daily.remaining_loss_budget)} USDT</b></span>
      <span><small>DEMO KANIT</small><b>%{v21?.certificate.score ?? 0}</b></span>
      <strong>GERÇEK PARA: 0 USDT · GERÇEK EMİR KANALI YOK</strong>
    </section>

    <nav className="v21Workflow" aria-label="Trading workflow">
      <div className="v21WorkflowTitle"><span>TRADING WORKFLOW</span><small>Current operating path</small></div>
      <div className="v21WorkflowSteps">
        {workflowSteps.map((step,index) => <button key={step.label} className={`v21WorkflowStep ${step.status} ${workflowCurrentIndex === index ? 'current' : ''}`} onClick={() => setTab(step.target)} aria-current={workflowCurrentIndex === index ? 'step' : undefined}>
          <i>{index + 1}</i><span><b>{step.label}</b><small>{step.status}</small></span>{index < workflowSteps.length - 1 && <em>→</em>}
        </button>)}
      </div>
    </nav>

    <section className="v21ExecutiveSummary" aria-label="Bot özeti">
      <div className="v21SummaryIntro"><span className="v21Eyebrow">BUGÜNÜN KONTROL MERKEZİ</span><h2>Bot şu anda ne yapıyor?</h2><p>{v21?.auto.rejection_reason || (v21?.auto.enabled ? 'Piyasayı izliyor ve yalnızca tüm güvenlik kapıları geçtiğinde Demo işlemi açıyor.' : 'Otomasyon kapalı. Başlamak için Demo kilidini ve ikinci onayı tamamlayın.')}</p><div className="v21NextAction"><span><small>NEXT BEST ACTION</small><b>{nextAction.label}</b><em>{nextAction.detail}</em></span><button onClick={() => setTab(nextAction.target)}>OPEN WORKSPACE <span>→</span></button></div></div>
      <div className="v21SummaryMetrics">
        <span><small>BOT DURUMU</small><b className={v21?.auto.enabled ? 'summaryPositive' : 'summaryMuted'}>{v21?.auto.enabled ? 'AKTİF' : 'KAPALI'}</b><em>{v21?.auto.rejection_gate ? gateLabel(v21.auto.rejection_gate) : 'Güvenlik izleniyor'}</em></span>
        <span><small>DEMO BAKİYESİ</small><b>{fmt(account?.wallet_balance)} USDT</b><em>Sanal hesap</em></span>
        <span><small>BUGÜN PnL</small><b className={(v21?.daily.realized_pnl || 0) >= 0 ? 'summaryPositive' : 'summaryNegative'}>{(v21?.daily.realized_pnl || 0) >= 0 ? '+' : ''}{fmt(v21?.daily.realized_pnl)} USDT</b><em>Gerçekleşen</em></span>
        <span><small>AÇIK POZİSYON</small><b>{v21?.account.positions ?? 0} / {v21?.settings.max_positions ?? 3}</b><em>Aktif / maksimum</em></span>
        <span><small>SONRAKİ TARAMA</small><b>{nextScanSeconds === null ? '—' : `${Math.floor(nextScanSeconds / 60)}:${String(nextScanSeconds % 60).padStart(2,'0')}`}</b><em>600 saniyelik döngü</em></span>
      </div>
      {v21?.auto.rejection_reason && <div className="v21SummaryBlock"><TriangleAlert/><span><b>İŞLEM AÇILMADI</b><strong>{gateLabel(v21.auto.rejection_gate)}</strong><small>{v21.auto.rejection_reason}</small></span></div>}
    </section>

    {tab === 'trade' && <section className="v21DashboardInsights" aria-label="Demo dashboard insights">
      <div className="v21InsightPanel v21AccountOverview"><header><div><span>ACCOUNT OVERVIEW</span><h2>Hesap Özeti</h2></div><Wallet/></header><div className="v21InsightMetrics">
        <span><small>TOTAL BALANCE</small><b>{fmt(overviewWallet)} <em>USDT</em></b></span><span><small>AVAILABLE BALANCE</small><b>{fmt(overviewAvailable)} <em>USDT</em></b></span><span><small>DAILY PnL</small><b className={(overviewPnl || 0) >= 0 ? 'demoProfit' : 'demoLoss'}>{overviewPnl === null || overviewPnl === undefined ? '—' : `${overviewPnl >= 0 ? '+' : ''}${fmt(overviewPnl)} USDT`}</b></span><span><small>OPEN POSITIONS</small><b>{account?.positions.length ?? v21?.account.positions ?? '—'}</b></span><span><small>USED MARGIN</small><b>{overviewUsedMargin === null ? '—' : `${fmt(overviewUsedMargin)} USDT`}</b></span><span><small>MARGIN USAGE</small><b className={overviewMarginUsage !== null && overviewMarginUsage > 70 ? 'demoLoss' : 'demoProfit'}>{overviewMarginUsage === null ? '—' : `%${overviewMarginUsage.toFixed(1)}`}</b></span><span><small>WIN RATE</small><b>{performance ? `%${performance.win_rate}` : '—'}</b></span>
      </div></div>
      <div className="v21InsightPanel v21DecisionIntelligence"><header><div><span>TRADE INTELLIGENCE</span><h2>Decision Intelligence</h2></div><Gauge/></header><div className="v21DecisionHeadline"><strong>{decisionCandidate ? fmt(decisionCandidate.score) : '—'}</strong><span>Decision Score · {decisionLabel}</span></div><p>{whyTrade}</p><div className="v21DecisionChecks">{decisionChecks.map(check => <span key={check.label}><small>{check.label}</small><b>{check.value}</b></span>)}</div><div className="v21IntelligenceActions"><button onClick={() => setTab('trade')}>ANALYZE SETUP</button><button onClick={() => setTab('risk')}>REVIEW RISK</button><button onClick={() => setTab('journal')}>VIEW POSITION TIMELINE</button></div></div>
      <div className={`v21InsightPanel v21RiskStatus ${riskClass}`}><header><div><span>RISK STATUS</span><h2>Risk Durumu</h2></div><ShieldCheck/></header>{riskLevel ? <><div className="v21RiskMeter"><i style={{width:`${Math.min(100,Math.max(8,100 - (riskDistance || 0) * 10))}%`}}/></div><strong>{riskLevel}</strong><p>Likidasyon mesafesi %{riskDistance?.toFixed(2)} · Kullanılan marjin {fmt(overviewUsedMargin)} USDT</p></> : <div className="v21InsightEmpty"><ShieldCheck/><span>Risk verisi henüz kullanılamıyor.</span></div>}</div>
      <div className="v21InsightPanel v21ProtectionCenter"><header><div><span>SMART RISK ENGINE · ADVISORY</span><h2>Protection Center</h2></div><ShieldCheck/></header><div className="v21ProtectionState"><b>{riskAvailable || account ? (riskClass === 'critical' ? 'PROTECTED' : riskClass === 'warning' ? 'CAUTION' : 'NORMAL') : 'UNAVAILABLE'}</b><span>{riskAvailable || account ? 'Recommended Protection' : 'Required protection data is unavailable.'}</span></div><div className="v21ProtectionMetrics"><span><small>DAILY PnL</small><b>{v21 ? `${fmt(v21.daily.realized_pnl)} USDT` : 'Unavailable'}</b></span><span><small>OPEN EXPOSURE</small><b>{account ? `${fmt(account.positions.reduce((total, position) => total + Math.abs(position.quantity * position.mark_price), 0))} USDT` : 'Unavailable'}</b></span><span><small>LOSS STREAK</small><b>{v21?.journal?.length ? `${v21.journal.slice(0,5).filter(item => (item.realized_pnl ?? 0) < 0).length}` : 'Unavailable'}</b></span></div></div>
      <div className="v21InsightPanel v21SmartAlerts"><header><div><span>SMART ALERTS</span><h2>Akıllı Uyarılar</h2></div><TriangleAlert/></header>{v21?.stream.last_error || v21?.scanner.last_error || v21?.auto.last_error ? <div className="v21AlertList">{[v21.stream.last_error,v21.scanner.last_error,v21.auto.last_error].filter(Boolean).map((alert,index) => <div className="warning" key={`${alert}-${index}`}><i/><span><b>ATTENTION</b><small>{alert}</small></span></div>)}</div> : <div className="v21InsightEmpty"><CheckCircle2/><span>Aktif risk uyarısı yok</span></div>}</div>
      <div className="v21InsightPanel v21QualityScore"><header><div><span>TRADE SETUP QUALITY</span><h2>Setup Kalitesi</h2></div><Gauge/></header>{qualityScore !== null ? <><div className="v21QualityHeadline"><b>{qualityScore.toFixed(0)}</b><span>/ 100 · {qualityLabel}</span></div><div className="v21QualityBars"><span><small>Top candidate score</small><i><b style={{width:`${qualityScore}%`}}/></i></span><span><small>Confidence</small><i><b style={{width:`${Math.min(100,Number(qualityCandidate?.confidence_value ?? 0))}%`}}/></i></span><span><small>Trend / volume</small><em>Detay verisi bekleniyor</em></span></div></> : <div className="v21InsightEmpty"><Gauge/><span>Setup quality verisi bekleniyor.</span></div>}</div>
      <div className="v21InsightPanel v21LiveActivity"><header><div><span>LIVE BOT ACTIVITY</span><h2>Canlı Bot Aktivitesi</h2></div><Activity/></header>{activityItems.length ? <div className="v21ActivityList">{activityItems.map((item,index) => <article key={`${item.time}-${index}`}><i/><div><b>{item.title}</b><span>{item.description}</span><small>{item.meta} · {stamp(item.time)}</small></div></article>)}</div> : <div className="v21InsightEmpty"><Activity/><span>Henüz bot aktivitesi yok.</span></div>}</div>
      <div className="v21InsightPanel v21LifecyclePanel"><header><div><span>POSITION LIFECYCLE</span><h2>Lifecycle Timeline</h2></div><Crosshair/></header>{lifecycleEvents.length ? <div className="v21LifecycleList">{lifecycleEvents.map(item => <article key={item.id}><i/><div><b>{item.kind}</b><span>{item.message}</span><small>{item.price !== null && item.price !== undefined ? `${fmt(item.price)} · ` : ''}{item.source}</small></div><time>{stamp(item.created_at)}</time></article>)}</div> : <div className="v21InsightEmpty"><Crosshair/><span>No detailed lifecycle events are available for this position yet.</span></div>}</div>
      <div className="v21InsightPanel v21ReplayPanel"><header><div><span>HISTORICAL EVENT REPLAY</span><h2>Trade Replay</h2></div><History/></header>{replayEvents.length ? <><div className="v21ReplaySummary"><b>{replayTrade.direction} · {symbol.replace('USDT','/USDT')}</b><span>Entry {fmt(replayTrade.entry)} · Exit {fmt(replayTrade.exit)} · PnL {fmt(replayTrade.pnl)}</span></div><div className="v21ReplaySteps">{replayEvents.map(event => <span key={event.label}><i/><b>{event.label}</b><small>{event.detail} · {new Date(event.time).toLocaleString('tr-TR')}</small></span>)}</div></> : <div className="v21InsightEmpty"><History/><span>No historical replay data available.</span></div>}</div>
      <div className="v21InsightPanel v21TradeHistory"><header><div><span>PROFESSIONAL TRADE HISTORY</span><h2>Trade History</h2></div><History/></header>{historyItems.length ? <div className="v21HistoryList">{historyItems.map((item,index) => <article key={`${item.entry_time}-${index}`}><b>{item.direction}</b><em className={item.direction === 'LONG' ? 'demoLong' : 'demoShort'}>{symbol.replace('USDT','/USDT')}</em><span>Giriş {fmt(item.entry)} · Çıkış {fmt(item.exit)}</span><strong className={item.pnl >= 0 ? 'demoProfit' : 'demoLoss'}>{item.pnl >= 0 ? '+' : ''}{fmt(item.pnl)}</strong><small>{item.pnl >= 0 ? 'WIN' : 'LOSS'} · {Math.max(0,Math.round((item.exit_time - item.entry_time) / 60000))} dk</small></article>)}</div> : <div className="v21InsightEmpty"><History/><span>Gerçek trade history verisi bekleniyor.</span></div>}</div>
      <div className="v21InsightPanel v21TradingJournal"><header><div><span>TRADING JOURNAL</span><h2>Karar Günlüğü</h2></div><ClipboardList/></header>{v21?.journal?.length ? <div className="v21JournalFeed">{v21.journal.slice(0,4).map(item => <article key={item.id}><i/><div><b>{item.kind}</b><span>{item.message}</span><small>{item.symbol || 'SİSTEM'} · {item.source} · {stamp(item.created_at)}</small></div></article>)}</div> : <div className="v21InsightEmpty"><ClipboardList/><span>İşlem kararı günlüğü bekleniyor.</span></div>}</div>
      <div className="v21InsightPanel v21PerformanceAnalytics"><header><div><span>DAILY PERFORMANCE ANALYTICS</span><h2>Günlük Performans</h2></div><BarChart3/></header>{performance ? <div className="v21PerformanceStats"><span><small>PnL</small><b className={performance.net_profit >= 0 ? 'demoProfit' : 'demoLoss'}>{fmt(performance.net_profit)} USDT</b></span><span><small>TRADES</small><b>{performance.total_trades}</b></span><span><small>WINS / LOSSES</small><b>{performance.wins} / {performance.losses}</b></span><span><small>WIN RATE</small><b>%{performance.win_rate}</b></span><span><small>BEST / WORST</small><b>{fmt(performance.best_trade)} / {fmt(performance.worst_trade)}</b></span></div> : <div className="v21InsightEmpty"><BarChart3/><span>Günlük performans verisi bekleniyor.</span></div>}</div>
    </section>}

    {tab === 'trade' && <section className="v21TradeIntelligenceStack">
      <article className="v21SafetyGate" aria-label="Pre-trade safety check"><header><div><span>PRE-TRADE SAFETY CHECK</span><h2>Review before order submission</h2></div><ShieldCheck/></header><div className="v21SafetySummary"><b>{safetySummary}</b><small>Advisory only · does not authorize execution</small></div><div className="v21SafetyChecks">{safetyChecks.map(check => <div className={`v21SafetyCheck ${check.status.toLowerCase()}`} key={check.label}><span><i/>{check.label}</span><b>{check.status}</b><small>{check.detail}</small></div>)}</div></article>
      <article className="v21SetupScore" aria-label="Setup score"><header><div><span>SETUP SCORE SYSTEM</span><h2>{setupScore === null ? 'Setup score unavailable' : `${setupScore} / 100`}</h2></div><strong>{setupRating}</strong></header><div className="v21ScoreBreakdown">{scoreFactors.map(factor => <div key={factor.label}><span><b>{factor.label}</b><small>{factor.value}</small></span><em>{factor.points === null ? 'Unavailable' : `+${factor.points}`}</em></div>)}</div><p className="v21WhyScore"><b>WHY THIS SCORE?</b>{qualityCandidate?.score !== undefined ? ` Scanner decision score is ${qualityCandidate.score}; available setup factors are shown separately.` : analysis?.direction ? ` ${analysis.direction} analysis is available, but scanner confidence is unavailable.` : ' Insufficient structured setup data for a reliable score.'}</p></article>
      <article className="v21DailyCoach" aria-label="Daily trading coach"><header><div><span>DAILY TRADING COACH</span><h2>Review insight</h2></div><ClipboardList/></header>{coachTrades.length ? <><p className="v21CoachObservation">Observation: {coachTrades.length} journal outcomes are available for review.</p><div className="v21CoachInsights"><span><small>BEST TRADE</small><b>{fmt(coachBest)} USDT</b></span><span><small>WORST TRADE</small><b>{fmt(coachWorst)} USDT</b></span><span><small>WIN / LOSS</small><b>{coachTrades.filter(item => (item.realized_pnl ?? 0) > 0).length} / {coachTrades.filter(item => (item.realized_pnl ?? 0) < 0).length}</b></span></div><small className="v21CoachNote">Use this as a review observation, not financial advice.</small></> : <div className="v21CoachEmpty">Not enough trading history for a reliable daily review.</div>}</article>
    </section>}

    {!status?.configured && <section className="demoSetupCard">
      <div><LockKeyhole/><span><b>Anahtarlar tarayıcıya yazılmaz</b><p>Proje klasöründeki <strong>BINANCE-DEMO-AYARLA.bat</strong> dosyasına çift tıklayın. Açılan siyah yerel pencereye Demo API Key ve Secret Key’i yapıştırın; sonra ProTreBot’u yeniden başlatın.</p></span></div>
      <button onClick={refreshStatus}><RefreshCw/> AYARI YENİDEN KONTROL ET</button>
    </section>}

    <section className={`demoCommandBar ${tab !== 'trade' ? 'demoTabHidden' : ''}`}>
      <button className="demoConnect" disabled={busy || !status?.configured} onClick={connect}><Radio/> BAĞLANTIYI TEST ET</button>
      <label><span>10 DAKİKALIK KİLİT İÇİN</span><input value={armText} onChange={event => setArmText(event.target.value)} placeholder="DEMO yaz"/></label>
      <button className={status?.armed ? 'demoLock' : 'demoUnlock'} disabled={busy || !status?.connected} onClick={status?.armed ? disarm : arm}>{status?.armed ? <LockKeyhole/> : <UnlockKeyhole/>}{status?.armed ? ' ŞİMDİ KİLİTLE' : ' DEMO EMRİNİ AÇ'}</button>
      <div><ShieldCheck/><span><b>DEMO GÜVENLİK SINIRI</b><small>100 USDT marjin · 2x · 200 USDT sanal pozisyon · 3 pozisyon</small></span></div>
      <button className="demoEmergency" disabled={busy || !status?.configured} onClick={emergency}><TriangleAlert/> ACİL DEMO DURDUR</button>
    </section>

    <div className={`demoMessage demoMessage-${messageKind}`}>{messageKind === 'error' ? <TriangleAlert/> : messageKind === 'ok' ? <ShieldCheck/> : <Activity/>}<span>{message}</span></div>

    {lastOrder && <section className="demoOrderConfirmation" aria-live="polite">
      <header><div><small>DEMO EMİR ONAYI</small><h3>Emir Binance Futures Demo hesabına iletildi</h3></div><CheckCircle2/></header>
      <div><span><small>Order ID</small><b>{lastOrder.order_id ?? '—'}</b></span><span><small>Parite</small><b>{lastOrder.symbol ?? symbol}</b></span><span><small>Yön</small><b>{lastOrder.side ?? '—'}</b></span><span><small>Tip</small><b>{lastOrder.type ?? form.orderType}</b></span><span><small>Miktar</small><b>{lastOrder.quantity ?? '—'}</b></span><span><small>Fiyat</small><b>{lastOrder.price ?? 'MARKET'}</b></span><span><small>Durum</small><b>{lastOrder.status ?? '—'}</b></span></div>
    </section>}

    <section className={`demoAccountStrip ${tab !== 'trade' ? 'demoTabHidden' : ''}`}>
      <article><Wallet/><span><small>SANAL CÜZDAN</small><b>{fmt(account?.wallet_balance)} USDT</b></span></article>
      <article><CircleDollarSign/><span><small>KULLANILABİLİR</small><b>{fmt(account?.available_balance)} USDT</b></span></article>
      <article><Activity/><span><small>AÇIK PnL</small><b className={(account?.unrealized_pnl || 0) >= 0 ? 'demoProfit' : 'demoLoss'}>{(account?.unrealized_pnl || 0) >= 0 ? '+' : ''}{fmt(account?.unrealized_pnl)} USDT</b></span></article>
      <article><Crosshair/><span><small>POZİSYON</small><b>{account?.reconciliation?.reconciled_active_positions ?? 0} / {status?.limits.max_open_positions ?? 3}</b></span></article>
      <article><Target/><span><small>AÇIK EMİRLER</small><b>{(account?.open_orders.length || 0)+(account?.open_algo_orders.length || 0)}</b></span></article>
      <article className={account?.hedge_mode ? 'demoModeBad' : 'demoModeGood'}><ShieldCheck/><span><small>POZİSYON MODU</small><b>{account ? account.hedge_mode ? 'HEDGE · DEĞİŞTİR' : 'ONE-WAY · UYGUN' : '—'}</b></span></article>
    </section>

    {chart && tab === 'trade' && <section className="demoLiveChart">
      <header><div><span>CANLI MUM GRAFİĞİ · EMA20 / EMA50 / EMA200</span><h3>{symbol.replace('USDT','/USDT')} Analiz ve Emir Seviyeleri</h3></div><div><b className={analysis?.direction === 'SHORT' ? 'demoLoss' : analysis?.direction === 'LONG' ? 'demoProfit' : ''}>{analysis?.direction || 'HESAPLANIYOR'}</b><small>Giriş {fmt(analysis?.entry)} · Stop {fmt(analysis?.stop_loss)} · TP3 {fmt(analysis?.tp3)}</small></div></header>
      <div className="demoChartCanvas">{chart}</div>
    </section>}

    <section className={`demoMainGrid ${tab !== 'trade' ? 'demoTabHidden' : ''}`}>
      <div className="demoTicket">
        <header><div><span>GÜVENLİ EMİR BİLETİ</span><h3>{symbol.replace('USDT','/USDT')}</h3></div><b>DEMO</b></header>
        <div className="demoSidePicker"><button className={form.direction === 'LONG' ? 'activeLong' : ''} onClick={() => setForm({...form,direction:'LONG'})}>LONG</button><button className={form.direction === 'SHORT' ? 'activeShort' : ''} onClick={() => setForm({...form,direction:'SHORT'})}>SHORT</button></div>
        <div className="demoTypePicker"><button className={form.orderType === 'MARKET' ? 'activeType' : ''} onClick={() => setForm({...form,orderType:'MARKET'})}>PİYASA</button><button className={form.orderType === 'LIMIT' ? 'activeType' : ''} onClick={() => setForm({...form,orderType:'LIMIT'})}>LİMİT</button></div>
        <button className="demoAnalysisFill" disabled={busy} onClick={fillFromAnalysis}><Activity/> {busy ? 'ANALİZ ALINIYOR…' : 'GÜNCEL ANALİZDEN DOLDUR'}</button>
        <div className="demoFieldGrid">
          <label><span>MARJİN · 5–100 DEMO USDT</span><div><input type="number" min="5" max="100" step="1" value={form.margin} onChange={event => changeMargin(event.target.value)} onBlur={normalizeMargin}/><em>USDT</em></div></label>
          <label><span>KALDIRAÇ</span><select value={form.leverage} onChange={event => setForm({...form,leverage:event.target.value as '1'|'2'})}><option value="1">1x</option><option value="2">2x</option></select></label>
          {form.orderType === 'LIMIT' && <label className="fullField"><span>LİMİT FİYATI</span><input value={form.limitPrice} onChange={event => setForm({...form,limitPrice:event.target.value})}/></label>}
          <label className="stopField"><span>STOP LOSS</span><input value={form.stop} onChange={event => setForm({...form,stop:event.target.value})}/></label>
          <label><span>TP1 · %30</span><input value={form.tp1} onChange={event => setForm({...form,tp1:event.target.value})}/></label>
          <label><span>TP2 · %30</span><input value={form.tp2} onChange={event => setForm({...form,tp2:event.target.value})}/></label>
          <label><span>TP3 · KALANI</span><input value={form.tp3} onChange={event => setForm({...form,tp3:event.target.value})}/></label>
        </div>
        <div className="demoExposure"><span><small>MAKS. POZİSYON</small><b>{fmt(numberValue(form.margin)*Number(form.leverage))} USDT</b></span><span><small>GERÇEK PARA</small><b>0 USDT</b></span></div>
        <button className="demoTest" disabled={busy || !status?.connected} onClick={testOrder}><TestTube2/> EMİR TESTİ · OLUŞTURMAZ</button>
        <button className="demoSubmit" disabled={busy || !status?.armed} onClick={submitOrder}><Send/> BINANCE DEMO EMRİ GÖNDER</button>
        <div className={`demoTicketFeedback demoTicketFeedback-${messageKind}`}>{messageKind === 'error' ? <TriangleAlert/> : messageKind === 'ok' ? <ShieldCheck/> : <Activity/>}<span><b>{messageKind === 'error' ? 'İŞLEM ENGELLENDİ' : messageKind === 'ok' ? 'DOĞRULAMA TAMAM' : 'GÜVENLİK DURUMU'}</b><small>{message}</small></span></div>
        <small className="demoTicketNote">Bu tutar yalnızca sanal Binance Demo bakiyesidir. Gerçek Binance emir kanalı kilitlidir.</small>
      </div>

      <div className="demoPositions">
        <header><div><span>CANLI DEMO POZİSYONLARI</span><h3>Giriş, Stop, TP ve Seviye Haritası</h3></div><b>{account?.reconciliation?.reconciled_active_positions ?? 0} AÇIK</b></header>
        <div className="demoPositionList">{account?.reconciliation?.reconciled_active_positions ? account.positions.map(position => <article key={position.symbol}>
          <header><div><b>{position.symbol.replace('USDT','/USDT')}</b><span className={position.direction === 'LONG' ? 'demoLong' : 'demoShort'}>{position.direction}</span><em className={position.leverage_verified ? 'demoVerified' : 'demoPending'}>{position.leverage_verified ? <ShieldCheck/> : <TriangleAlert/>}{position.leverage ? `${position.leverage}x` : '—'} · {(position.margin_type || 'DOĞRULANIYOR').toUpperCase()}</em></div><strong className={position.unrealized_pnl >= 0 ? 'demoProfit' : 'demoLoss'}>{position.unrealized_pnl >= 0 ? '+' : ''}{fmt(position.unrealized_pnl)} USDT</strong></header>
          <div className="demoPositionMetrics"><span><small>Miktar</small><b>{fmt(position.quantity)}</b></span><span><small>Giriş</small><b>{fmt(position.entry_price)}</b></span><span><small>Canlı</small><b>{fmt(position.mark_price)}</b></span><span><small>Likidasyon</small><b>{fmt(position.liquidation_price)}</b></span></div>
          <div className="demoPositionMeta"><span><small>İstenen kaldıraç</small><b>{position.requested_leverage || activePlanBySymbol.get(position.symbol)?.requested_leverage || activePlanBySymbol.get(position.symbol)?.leverage || '—'}x</b></span><span><small>Uygulanan kaldıraç</small><b>{position.applied_leverage || position.leverage || '—'}x · {(position.margin_type || '—').toUpperCase()}</b></span></div>
          <div className={`demoLeverageAudit ${position.leverage_verified ? 'verified' : 'pending'}`}>{position.leverage_verified ? <ShieldCheck/> : <TriangleAlert/>}<span><small>KALDIRAÇ VE MARJİN DENETİMİ</small><b>{position.leverage_verified ? `Binance doğruladı: ${position.leverage}x ISOLATED` : 'Binance yapılandırması doğrulanıyor; değer uydurulmuyor.'}</b></span></div>
          <PositionMap position={position} plan={activePlanBySymbol.get(position.symbol)}/>
          <footer><span>{activePlanBySymbol.get(position.symbol)?.monitoring_targets?.length ? `${activePlanBySymbol.get(position.symbol)?.monitoring_targets?.join(', ')} izleme hedefi` : 'Koşullu koruma kontrol ediliyor'}</span><button disabled={busy} onClick={() => closePosition(position)}>DEMO POZİSYONU KAPAT</button></footer>
        </article>) : <div className="demoEmpty"><Crosshair/><b>Açık Demo pozisyonu yok</b><span>Bağlantı kurulduğunda Binance Demo hesabındaki pozisyonlar burada canlı görünür.</span></div>}</div>
      </div>
    </section>

    {tab === 'trade' && <section className="v21PositionAssistant" aria-label="Position Management Assistant"><header><div><span>POSITION MANAGEMENT ASSISTANT · ADVISORY</span><h2>Position Management Assistant</h2><p>Monitor protection, distance and lifecycle context from the current account state.</p></div><Crosshair/></header>{positionAssistant.length ? <div className="v21PositionCards">{positionAssistant.map(item => <article className="v21PositionCard" key={item.position.symbol}><div className="v21PositionCardHead"><b>{item.position.symbol.replace('USDT','/USDT')}</b><span>{item.position.direction}</span><strong>{item.stage}</strong></div><div className="v21PositionMetrics"><span><small>ENTRY</small><b>{fmt(item.entry)}</b></span><span><small>CURRENT</small><b>{fmt(item.position.mark_price)}</b></span><span><small>UNREALIZED PnL</small><b className={item.position.unrealized_pnl >= 0 ? 'demoProfit' : 'demoLoss'}>{fmt(item.position.unrealized_pnl)}</b></span><span><small>STOP DISTANCE</small><b>{item.stopDistance === null ? 'Unavailable' : `%${item.stopDistance.toFixed(2)}`}</b></span><span><small>TARGET DISTANCE</small><b>{item.targetDistance === null ? 'Unavailable' : `%${item.targetDistance.toFixed(2)}`}</b></span><span><small>R/R</small><b>{item.rr === null ? 'Unavailable' : `${item.rr.toFixed(2)}R`}</b></span></div><p className="v21PositionObservation">{item.observation}</p></article>)}</div> : <div className="v21PositionAssistantEmpty">No active positions available for position management review.</div>}</section>}

    <section className={`demoOrdersGrid ${tab !== 'trade' ? 'demoTabHidden' : ''}`}>
      <div className="demoOrderPanel"><header><div><span>BEKLEYEN GİRİŞLER</span><h3>Normal Demo Emirleri</h3></div><b>{account?.open_orders.length ?? 0}</b></header><div>{account?.open_orders.length ? account.open_orders.map(order => <article key={order.order_id}><span><b>{order.symbol} · {order.side}</b><small>{order.type} · {order.status}</small></span><em>{fmt(order.price || undefined)} · {fmt(order.quantity)}</em><button disabled={busy} onClick={() => cancelOrder(order)}>İPTAL</button></article>) : <p>Açık normal Demo emri yok.</p>}</div></div>
      <div className="demoOrderPanel"><header><div><span>STOP / TAKE PROFIT</span><h3>Koşullu Koruma Emirleri</h3></div><b>{account?.open_algo_orders.length ?? 0}</b></header><div>{account?.open_algo_orders.length ? account.open_algo_orders.map(order => <article key={order.algo_id}><span><b>{order.symbol} · {order.type}</b><small>{order.status} · {order.close_position ? 'Pozisyonu kapatır' : 'Kısmi azaltır'}</small></span><em>Tetik {fmt(order.trigger_price)}</em><button disabled={busy} onClick={() => cancelAlgo(order)}>İPTAL</button></article>) : <p>Açık koşullu Demo emri yok.</p>}</div></div>
      <div className="demoEventPanel"><header><div><span>DENETİM AKIŞI</span><h3>Son Güvenlik Olayları</h3></div><b>{status?.events.length ?? 0}</b></header><div>{status?.events.slice(0,6).map((event,index) => <article key={`${event.created_at}-${index}`}><i/><span><b>{event.kind}</b><small>{event.message}</small></span><time>{stamp(event.created_at)}</time></article>)}</div></div>
    </section>

    {tab === 'risk' && <section ref={workspaceRef} className="v21Workspace">
      <header className="v21WorkspaceHead"><div><span>V21 · KAYIP ÖNCE HESAPLANIR</span><h2>Risk Kasası ve Pozisyon Boyutlandırıcı</h2><p>“Kaç USDT yatırayım?” yerine “Stop olursa en fazla kaç USDT kaybedeyim?” sorusundan başlar.</p></div><div className="v21HeaderActions"><b><ShieldCheck/> DEMO HARD CAP · 100 USDT · 2X</b><button className="v21ContextCta" onClick={() => setTab('trade')}>RETURN TO TRADE DESK →</button></div></header>
      <div className="v21RiskLayout">
        <article className="v21Card v21Calculator"><header><Calculator/><div><small>SEÇİLİ PLAN</small><h3>{symbol.replace('USDT','/USDT')} Risk Hesabı</h3></div></header><div className="v21CalcQuote"><span><small>GİRİŞ</small><b>{fmt(analysis?.entry)}</b></span><span><small>STOP</small><b>{fmt(analysis?.stop_loss)}</b></span><label><small>MAKS. KAYIP</small><div><input value={riskLoss} onChange={event => setRiskLoss(event.target.value)}/><em>USDT</em></div></label></div><button disabled={v21Busy || !analysis} onClick={calculateRisk}><Calculator/> GÜVENLİ BOYUTU HESAPLA</button>{riskPreview ? <div className="v21RiskResult"><span><small>MARJİN</small><b>{fmt(riskPreview.margin_usdt)} USDT</b></span><span><small>POZİSYON</small><b>{fmt(riskPreview.notional_usdt)} USDT</b></span><span><small>STOP KAYBI</small><b>{fmt(riskPreview.estimated_stop_loss_usdt)} USDT</b></span><span><small>FİYAT RİSKİ</small><b>%{fmt(riskPreview.risk_pct)}</b></span><p>{riskPreview.capped ? 'Hard cap uygulandı; istenen kayıp bütçesinin tamamı kullanılmadı.' : 'Hesap kullanıcı kayıp limitine göre boyutlandı.'}</p></div> : <div className="v21EmptyMini">Güncel analizden giriş/stop geldikten sonra hesapla.</div>}</article>
        <article className="v21Card v21Settings"><header><Settings2/><div><small>YEREL GÜVENLİK POLİTİKASI</small><h3>Risk ve Koruma Limitleri</h3></div></header>{settingsDraft && <div className="v21SettingsGrid">
          <label><span>İşlem başı maks. kayıp</span><input type="number" min=".5" max="25" value={settingsDraft.max_loss_per_trade} onChange={event => setSettingsDraft({...settingsDraft,max_loss_per_trade:Number(event.target.value)})}/><em>USDT</em></label>
          <label><span>İşlem başı maks. marjin</span><input type="number" min="5" max="100" value={settingsDraft.max_margin_per_trade} onChange={event => setSettingsDraft({...settingsDraft,max_margin_per_trade:Number(event.target.value)})}/><em>USDT</em></label>
          <label><span>Günlük zarar kilidi</span><input type="number" min="5" max="250" value={settingsDraft.daily_loss_limit} onChange={event => setSettingsDraft({...settingsDraft,daily_loss_limit:Number(event.target.value)})}/><em>USDT</em></label>
          <label><span>Günlük işlem limiti</span><input type="number" min="1" max="30" value={settingsDraft.daily_trade_limit} onChange={event => setSettingsDraft({...settingsDraft,daily_trade_limit:Number(event.target.value)})}/><em>adet</em></label>
          <label><span>Aynı anda pozisyon</span><select value={settingsDraft.max_positions} onChange={event => setSettingsDraft({...settingsDraft,max_positions:Number(event.target.value)})}><option value="1">1</option><option value="2">2</option><option value="3">3</option></select></label>
          <label><span>Minimum güven</span><input type="number" min="60" max="95" value={settingsDraft.min_confidence} onChange={event => setSettingsDraft({...settingsDraft,min_confidence:Number(event.target.value)})}/><em>%</em></label>
          <label className="v21Switch"><input type="checkbox" checked={settingsDraft.breakeven_enabled} onChange={event => setSettingsDraft({...settingsDraft,breakeven_enabled:event.target.checked})}/><span><b>Başabaş Stop</b><small>{settingsDraft.breakeven_trigger_r}R sonrası</small></span></label>
          <label className="v21Switch"><input type="checkbox" checked={settingsDraft.trailing_enabled} onChange={event => setSettingsDraft({...settingsDraft,trailing_enabled:event.target.checked})}/><span><b>İz Süren Stop</b><small>{settingsDraft.trailing_trigger_r}R sonrası</small></span></label>
        </div>}<button disabled={v21Busy || !settingsDraft} onClick={saveSettings}><Save/> RİSK POLİTİKASINI KAYDET</button></article>
      </div>
      <div className="v21MetricRow"><span><small>GÜNLÜK GERÇEKLEŞEN</small><b className={(v21?.daily.realized_pnl || 0) >= 0 ? 'demoProfit' : 'demoLoss'}>{fmt(v21?.daily.realized_pnl)} USDT</b></span><span><small>KALAN ZARAR BÜTÇESİ</small><b>{fmt(v21?.daily.remaining_loss_budget)} USDT</b></span><span><small>STOP ONARIMI</small><b>{v21?.protection.repairs ?? 0}</b></span><span><small>YİNELENEN GİRİŞ ENGELİ</small><b>{v21?.protection.duplicate_blocks ?? 0}</b></span></div>
    </section>}

    {tab === 'journal' && <section ref={workspaceRef} className="v21Workspace">
      <header className="v21WorkspaceHead"><div><span>ORDER_TRADE_UPDATE · ALGO_UPDATE · REST EŞLEŞTİRME</span><h2>Canlı Demo İşlem Günlüğü</h2><p>Açılış, kısmi dolum, kapanış, Stop/TP değişimi ve engelleme nedeni tek zaman çizgisinde.</p></div><div className="v21HeaderActions"><button disabled={v21Busy || !status?.connected} onClick={loadHistory}><History/> {symbol} BORSA GEÇMİŞİNİ GETİR</button><button className="v21ContextCta" onClick={() => setTab('performance')}>REVIEW PERFORMANCE →</button></div></header>
      <div className="v21JournalStats"><span><small>BUGÜN OLAY</small><b>{v21?.daily.events ?? 0}</b></span><span><small>USER STREAM</small><b>{v21?.stream.status || '—'}</b></span><span><small>SON EŞLEŞTİRME</small><b>{stamp(v21?.stream.last_sync)}</b></span><span><small>YENİDEN BAĞLANTI</small><b>{v21?.stream.reconnect_count ?? 0}</b></span></div>
      <div className="v21JournalGrid"><article className="v21Card v21Timeline"><header><ClipboardList/><div><small>KALICI YEREL KAYIT</small><h3>V21 Olay Zaman Çizgisi</h3></div><b>{v21?.journal.length ?? 0}</b></header><div>{v21?.journal.length ? v21.journal.map(item => <section key={item.id}><i className={item.realized_pnl && item.realized_pnl < 0 ? 'bad' : ''}/><div><span><b>{item.kind}</b><em>{item.symbol || 'SİSTEM'} · {item.source}</em></span><p>{item.message}</p>{item.reason && <small>{item.reason}</small>}</div><aside><time>{stamp(item.created_at)}</time>{item.realized_pnl !== null && item.realized_pnl !== undefined && <strong className={item.realized_pnl >= 0 ? 'demoProfit' : 'demoLoss'}>{item.realized_pnl >= 0 ? '+' : ''}{fmt(item.realized_pnl)}</strong>}</aside></section>) : <div className="v21EmptyMini">İlk Demo olayı bekleniyor.</div>}</div></article>
        <article className="v21Card v21ExchangeHistory"><header><History/><div><small>BINANCE FUTURES DEMO</small><h3>{symbol} Emir / Dolum Arşivi</h3></div></header>{historyPayload ? <div><h4>NORMAL EMİRLER · {historyPayload.orders.length}</h4>{historyPayload.orders.slice(-12).reverse().map((row,index) => <p key={`o-${index}`}><b>{String(row.side ?? '—')} · {String(row.type ?? '—')}</b><span>{String(row.status ?? '—')} · {String(row.avgPrice ?? row.price ?? '—')}</span></p>)}<h4>KOŞULLU EMİRLER · {historyPayload.algo_orders.length}</h4>{historyPayload.algo_orders.slice(-8).reverse().map((row,index) => <p key={`a-${index}`}><b>{String(row.orderType ?? row.type ?? 'ALGO')}</b><span>{String(row.algoStatus ?? row.status ?? '—')} · {String(row.triggerPrice ?? '—')}</span></p>)}<h4>DOLUMLAR · {historyPayload.trades.length}</h4>{historyPayload.trades.slice(-8).reverse().map((row,index) => <p key={`t-${index}`}><b>{String(row.side ?? '—')} · {String(row.qty ?? '—')}</b><span>PnL {String(row.realizedPnl ?? '0')} · ücret {String(row.commission ?? '—')}</span></p>)}</div> : <div className="v21EmptyMini">Üstteki düğmeyle seçili paritenin tam Demo geçmişini getir.</div>}</article>
      </div>
    </section>}

    {tab === 'performance' && <section className="v21PerformanceAnalytics" aria-label="Advanced Performance Analytics"><header><div><span>ADVANCED PERFORMANCE ANALYTICS · READ ONLY</span><h2>Advanced Performance Analytics</h2><p>Derived from realized journal outcomes and the existing performance response.</p></div><BarChart3/></header><div className="v21PerformanceMetrics"><span><small>TOTAL TRADES</small><b>{analyticsCount ?? 'Unavailable'}</b></span><span><small>WIN RATE</small><b>{analyticsWinRate === null ? 'Unavailable' : `%${analyticsWinRate.toFixed(2)}`}</b></span><span><small>REALIZED PnL</small><b>{analyticsTotal === null ? 'Unavailable' : `${fmt(analyticsTotal)} USDT`}</b></span><span><small>AVERAGE WIN</small><b>{analyticsAverageWin === null ? 'Unavailable' : `${fmt(analyticsAverageWin)} USDT`}</b></span><span><small>AVERAGE LOSS</small><b>{analyticsAverageLoss === null ? 'Unavailable' : `${fmt(analyticsAverageLoss)} USDT`}</b></span><span><small>PROFIT FACTOR</small><b>{analyticsProfitFactor === null ? 'Unavailable' : analyticsProfitFactor.toFixed(2)}</b></span><span><small>EXPECTANCY</small><b>{analyticsExpectancy === null ? 'Unavailable' : `${fmt(analyticsExpectancy)} USDT`}</b></span></div><div className="v21StreakPanel"><b>STREAK ANALYSIS</b><span>{analyticsTrades.length ? 'Trade order unavailable for reliable streak analysis.' : 'Insufficient data for streak analysis.'}</span></div><div className="v21DirectionAnalytics"><b>LONG VS SHORT</b><span>{analyticsTrades.some(item => item.side) ? 'Direction breakdown available from journal sides.' : 'Direction data unavailable.'}</span></div><div className="v21PerformanceCurve">{analyticsTrades.length >= 2 ? <span>Ordered equity curve requires reliable event ordering.</span> : <span>Trade ordering unavailable for reliable drawdown analysis. No performance curve rendered.</span>}</div></section>}

    {tab === 'performance' && <section ref={workspaceRef} className="v21Workspace v21PerformanceCenter">
      <header className="v21WorkspaceHead"><div><span>GERÇEK KAPANIŞ EVENTLERİ · READ ONLY</span><h2>Performance Center</h2><p>Sonuçlar yalnızca kapanmış Demo işlemlerinden ve backend journal kayıtlarından hesaplanır.</p></div><div className="v21HeaderActions"><div className="v21PeriodPicker">{(['all','daily','weekly','monthly'] as const).map(period => <button key={period} className={performancePeriod === period ? 'active' : ''} onClick={() => setPerformancePeriod(period)}>{period === 'all' ? 'TÜMÜ' : period === 'daily' ? 'GÜNLÜK' : period === 'weekly' ? 'HAFTALIK' : 'AYLIK'}</button>)}</div><button className="v21ContextCta" onClick={() => setTab('trade')}>BACK TO COMMAND CENTER →</button></div></header>
      {performance ? <><div className="v21PerformanceHero"><span><small>NET PROFIT</small><b className={performance.net_profit >= 0 ? 'demoProfit' : 'demoLoss'}>{performance.net_profit >= 0 ? '+' : ''}{fmt(performance.net_profit)} USDT</b><em>{performance.total_trades} kapanmış işlem</em></span><span><small>WIN RATE</small><b>{fmt(performance.win_rate)}%</b><em>{performance.wins} kazanç · {performance.losses} kayıp</em></span><span><small>PROFIT FACTOR</small><b>{fmt(performance.profit_factor)}</b><em>Gerçekleşen PnL</em></span><span><small>MAX DRAWDOWN</small><b className="demoLoss">{fmt(performance.max_drawdown)} USDT</b><em>Dönem içi</em></span></div><div className="v21PerformanceGrid">{[['TOPLAM KÂR',performance.total_profit,'demoProfit'],['TOPLAM ZARAR',performance.total_loss,'demoLoss'],['ORTALAMA İŞLEM',performance.average_trade,performance.average_trade >= 0 ? 'demoProfit' : 'demoLoss'],['EN İYİ İŞLEM',performance.best_trade,'demoProfit'],['EN KÖTÜ İŞLEM',performance.worst_trade,'demoLoss']].map(([label,value,kind]) => <article key={String(label)}><small>{label}</small><b className={String(kind)}>{Number(value) >= 0 ? '+' : ''}{fmt(Number(value))} USDT</b></article>)}</div></> : <div className="v21LargeEmpty"><BarChart3/><b>Performance verisi bekleniyor</b><span>Read-only kapanış kayıtları yükleniyor.</span></div>}
    </section>}

    {tab === 'auto' && <section ref={workspaceRef} className="v21Workspace">
      <header className="v21WorkspaceHead"><div><span>ÇİFT ONAY · DEMO ARM + DEMO OTOMATİK</span><h2>Kontrollü Demo Otopilot</h2><p>İzin listesi, yön, saat, güven, volatilite, korelasyon, günlük kayıp ve pozisyon kapıları birlikte geçmeden emir göndermez.</p></div><div className="v21HeaderActions"><b className={v21?.auto.enabled ? 'v21Running' : 'v21Stopped'}><Zap/> {v21?.auto.enabled ? 'ÇALIŞIYOR' : 'GÜVENLİ KAPALI'}</b><button className="v21ContextCta" onClick={() => setTab('trade')}>OPEN TRADE SETUP →</button></div></header>
      <div className="v21AutoLayout"><article className="v21Card v21AutoControl"><header><Zap/><div><small>İKİNCİ KULLANICI ONAYI</small><h3>Demo Otomasyon Motoru</h3></div></header><div className="v21AutoDecision"><small>SON KARAR</small><b>{v21?.auto.last_decision || 'Bekleniyor'}</b><span>{v21?.auto.last_scan ? `Son tarama ${stamp(v21.auto.last_scan)} · ${v21.auto.cycles} tur` : 'Henüz tarama yapılmadı.'}</span>{v21?.auto.rejection_reason && <em>İşlem Açılmadı · {v21.auto.rejection_gate}: {v21.auto.rejection_reason}</em>}</div>{!v21?.auto.enabled && <label><span>Başlatmak için yaz</span><input value={autoConfirm} onChange={event => setAutoConfirm(event.target.value)} placeholder="DEMO OTOMATİK"/></label>}<button className={v21?.auto.enabled ? 'stop' : ''} disabled={v21Busy || (!v21?.auto.enabled && !status?.armed)} onClick={toggleAuto}>{v21?.auto.enabled ? <TriangleAlert/> : <Play/>}{v21?.auto.enabled ? ' YENİ GİRİŞLERİ DURDUR' : ' KONTROLLÜ DEMO OTOMASYONU BAŞLAT'}</button><button disabled={v21Busy || !v21?.scanner.top_candidates.length} onClick={runSmokeTest}><TestTube2/> DEMO İŞLEMİ TEST ET</button><p>Uygulama yeniden açıldığında daima kapalı başlar. Stop/TP koruması motor dursa bile Binance Demo hesabında kalır.</p></article>
        <article className="v21Card v21AutoRules"><header><Settings2/><div><small>OTOMASYON EVRENİ</small><h3>İzinler ve Piyasa Kapıları</h3></div></header>{settingsDraft && <div>
          <label className="wide"><span>İzinli USDT pariteleri</span><input value={settingsDraft.allowed_symbols.join(', ')} onChange={event => setSettingsDraft({...settingsDraft,allowed_symbols:event.target.value.toUpperCase().split(',').map(value => value.trim()).filter(Boolean)})}/></label>
          <label><span>Maks. volatilite</span><input type="number" value={settingsDraft.max_volatility_pct} onChange={event => setSettingsDraft({...settingsDraft,max_volatility_pct:Number(event.target.value)})}/><em>%</em></label>
          <label><span>Maks. BTC korelasyonu</span><input type="number" value={settingsDraft.max_correlation_pct} onChange={event => setSettingsDraft({...settingsDraft,max_correlation_pct:Number(event.target.value)})}/><em>%</em></label>
          <label><span>Başlangıç saati</span><input type="number" min="0" max="23" value={settingsDraft.schedule_start_hour} onChange={event => setSettingsDraft({...settingsDraft,schedule_start_hour:Number(event.target.value)})}/></label>
          <label><span>Bitiş saati</span><input type="number" min="1" max="24" value={settingsDraft.schedule_end_hour} onChange={event => setSettingsDraft({...settingsDraft,schedule_end_hour:Number(event.target.value)})}/></label>
          <label className="v21Switch"><input type="checkbox" checked={settingsDraft.allow_long} onChange={event => setSettingsDraft({...settingsDraft,allow_long:event.target.checked})}/><span><b>LONG izinli</b></span></label>
          <label className="v21Switch"><input type="checkbox" checked={settingsDraft.allow_short} onChange={event => setSettingsDraft({...settingsDraft,allow_short:event.target.checked})}/><span><b>SHORT izinli</b></span></label>
        </div>}<button disabled={v21Busy || !settingsDraft} onClick={saveSettings}><Save/> OTOMASYON KAPILARINI KAYDET</button></article></div>
      <article className="v21Card v21AutoScanner"><header><div className="v21ScannerTitle"><span className="v21ScannerIcon"><Gauge/></span><div><small>100 USDT PERPETUAL TARAMA</small><h3>Bot Durumu ve En İyi Fırsatlar</h3></div></div><b className={`v21ScannerStatus v21ScannerStatus-${(v21?.scanner.scan_status || 'BEKLEMEDE').toLowerCase()}`}>{v21?.scanner.scan_status || v21?.scanner.last_stage || 'BEKLEMEDE'}</b></header><div className="v21ScannerStats"><span><small>TARANAN COIN</small><b>{v21?.scanner.coins_scanned ?? 0}</b><em>USDT perpetual</em></span><span><small>UYGUN FIRSAT</small><b>{v21?.scanner.selected_count ?? v21?.scanner.eligible_count ?? 0}</b><em>Top fırsat</em></span><span><small>AÇIK POZİSYON</small><b>{v21?.account.positions ?? 0}/{v21?.settings.max_positions ?? 3}</b><em>Risk limiti</em></span><span><small>SON TARAMA</small><b>{stamp(v21?.scanner.last_scan_at)}</b><em>Güncel veri</em></span><span><small>SONRAKİ TARAMA</small><b>{stamp(v21?.scanner.next_scan_at)}</b><em>600 sn döngü</em></span></div><div className="v21ScannerResults"><div className="v21ScannerResultsHead"><div><small>BUGÜNÜN EN İYİ FIRSATLARI</small><h4>Skora göre sıralanan sinyaller</h4></div><span>{v21?.scanner.top_candidates.length ?? 0} sonuç</span></div>{v21?.scanner.top_candidates.length ? <div className="v21ScannerCards">{v21.scanner.top_candidates.map((candidate,index) => <article className={`v21Opportunity v21Opportunity-${candidate.direction.toLowerCase()}`} key={candidate.symbol}><header><div><small>#{candidate.rank || index + 1}</small><b>{candidate.symbol.replace('USDT','/USDT')}</b></div><em>{candidate.direction}</em></header><div className="v21OpportunityScore"><strong>{candidate.score.toFixed(0)}</strong><span>/ 100</span><i><b style={{width:`${Math.max(0,Math.min(100,candidate.score))}%`}}/></i></div><div className="v21OpportunityMeta"><span><small>GÜVEN</small><b>{candidate.confidence}</b></span>{candidate.trend && <span><small>TREND</small><b>{candidate.trend}</b></span>}{candidate.volatility_pct !== undefined && <span><small>VOLATİLİTE</small><b>%{candidate.volatility_pct.toFixed(2)}</b></span>}</div>{candidate.reasons?.length ? <ul>{candidate.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul> : <p className="v21NoReason">Sinyal nedeni mevcut değil.</p>}</article>)}</div> : <div className="v21ScannerEmpty"><Gauge/><b>{v21?.scanner.last_error || 'Henüz uygun fırsat bulunamadı.'}</b><span>Yeni tarama bekleniyor.</span></div>}</div></article>
      <div className="v21GateStrip"><span className={status?.armed ? 'passed' : ''}><b>1</b><em>DEMO ARM</em><small>{status?.armed ? 'GEÇTİ' : 'KAPALI'}</small></span><span className={status?.connected ? 'passed' : ''}><b>2</b><em>DEMO API</em><small>{status?.connected ? 'BAĞLI' : 'BEKLİYOR'}</small></span><span className={(v21?.daily.auto_entries || 0) < (v21?.settings.daily_trade_limit || 0) ? 'passed' : ''}><b>3</b><em>GÜNLÜK LİMİT</em><small>{v21?.daily.auto_entries ?? 0}/{v21?.settings.daily_trade_limit ?? 0}</small></span><span className={(v21?.daily.remaining_loss_budget || 0) > 0 ? 'passed' : ''}><b>4</b><em>ZARAR KASASI</em><small>{fmt(v21?.daily.remaining_loss_budget)} USDT</small></span><span className={(v21?.account.reconciled_active_positions ?? 0) < (v21?.settings.max_positions || 0) ? 'passed' : ''}><b>5</b><em>POZİSYON</em><small>{v21?.account.reconciled_active_positions ?? 0}/{v21?.settings.max_positions ?? 0}</small></span><span><b>6</b><em>SİNYAL KAPILARI</em><small>Her taramada</small></span></div>
    </section>}

    {tab === 'backtest' && <section ref={workspaceRef} className="v21Workspace">
      <header className="v21WorkspaceHead"><div><span>NO LOOK-AHEAD · NEXT OPEN · STOP FIRST</span><h2>Kanıtlı Backtest Laboratuvarı</h2><p>Sinyal kapanan mumdan, giriş sonraki mum açılışından alınır; ücret ve kayma iki yönlü düşülür.</p></div><div className="v21HeaderActions"><div className="v21BacktestRun"><select value={backtestSymbol} onChange={event => setBacktestSymbol(event.target.value)}>{(v21?.settings.allowed_symbols || [symbol]).map(item => <option key={item}>{item}</option>)}</select><button disabled={v21Busy || !status?.configured} onClick={runBacktest}><BarChart3/> 1.000 MUMU TEST ET</button></div><button className="v21ContextCta" onClick={() => setTab('performance')}>REVIEW PERFORMANCE →</button></div></header>
      {v21?.backtest ? <><div className="v21BacktestMetrics"><span><small>NET SONUÇ</small><b className={v21.backtest.net_pnl >= 0 ? 'demoProfit' : 'demoLoss'}>{v21.backtest.net_pnl >= 0 ? '+' : ''}{fmt(v21.backtest.net_pnl)} USDT</b></span><span><small>İŞLEM</small><b>{v21.backtest.trades}</b></span><span><small>BAŞARI</small><b>%{fmt(v21.backtest.win_rate)}</b></span><span><small>MAKS. DÜŞÜŞ</small><b>%{fmt(v21.backtest.max_drawdown_pct)}</b></span><span><small>PROFIT FACTOR</small><b>{fmt(v21.backtest.profit_factor)}</b></span><span><small>GELECEK SIZINTISI</small><b>{v21.backtest.no_lookahead ? 'YOK' : 'KONTROL'}</b></span></div><div className="v21BacktestLayout"><article className="v21Card v21Folds"><header><BarChart3/><div><small>3 DÖNEMLİ ZAMAN TÜNELİ</small><h3>Geliştirme · Doğrulama · Görünmeyen</h3></div></header>{v21.backtest.folds.map((fold,index) => <section key={fold.name}><b>{index+1}</b><span><strong>{fold.name}</strong><small>{fold.trades} işlem</small></span><em className={fold.net_pnl >= 0 ? 'demoProfit' : 'demoLoss'}>{fold.net_pnl >= 0 ? '+' : ''}{fmt(fold.net_pnl)} USDT</em></section>)}</article><article className="v21Card v21TradeResults"><header><History/><div><small>SON İŞLEMLER</small><h3>Maliyet Sonrası Sonuçlar</h3></div></header><div>{v21.backtest.recent_trades.slice(0,16).map((trade,index) => <p key={index}><span><b>{trade.direction} · {trade.reason}</b><small>{trade.regime} · maliyet {fmt(trade.cost_usdt)}</small></span><em className={trade.pnl >= 0 ? 'demoProfit' : 'demoLoss'}>{trade.pnl >= 0 ? '+' : ''}{fmt(trade.pnl)}</em></p>)}</div></article></div><p className="v21Disclaimer">{v21.backtest.note}</p></> : <div className="v21LargeEmpty"><BarChart3/><b>Henüz V21 backtest çalıştırılmadı</b><span>Seçili paritede 1.000 Demo Futures mumunu kronolojik olarak sınamak için üstteki düğmeye bas.</span></div>}
    </section>}

    {tab === 'certificate' && <section ref={workspaceRef} className="v21Workspace">
      <header className="v21WorkspaceHead"><div><span>V21 DEMO DISCIPLINE CERTIFICATE</span><h2>Sistem Sağlığı ve Demo Sertifikası</h2><p>Sertifika kâr vaadi değildir; yalnızca Demo kanıtı, koruma, tekrar, bağlantı ve düşüş eşiklerini ölçer.</p></div><b className={v21?.certificate.status === 'DEMO SERTİFİKALI' ? 'v21Running' : 'v21Pending'}><ShieldCheck/> {v21?.certificate.status || 'KANIT BEKLİYOR'}</b></header>
      <div className="v21CertificateLayout"><article className="v21Card v21Score"><div className="v21ScoreRing" style={{'--score':`${v21?.certificate.score || 0}%`} as CSSProperties}><span><b>%{v21?.certificate.score ?? 0}</b><small>DEMO KANIT</small></span></div><h3>{v21?.certificate.passed_gates ?? 0} / {v21?.certificate.total_gates ?? 0} kapı geçti</h3><p>{v21?.certificate.reason}</p><button onClick={enableNotifications}><Bell/> MASAÜSTÜ BİLDİRİMLERİNİ AÇ</button></article><article className="v21Card v21CertificateGates"><header><ShieldCheck/><div><small>ZORUNLU KANIT KAPILARI</small><h3>V21 Kontrol Listesi</h3></div></header><div>{v21?.certificate.gates.map(gate => <section className={gate.passed ? 'passed' : ''} key={gate.name}><i>{gate.passed ? '✓' : '!'}</i><span><b>{gate.name}</b><small>Hedef: {gate.target}</small></span><strong>{gate.value}</strong></section>)}</div></article><article className="v21Card v21Health"><header><Activity/><div><small>BAĞLANTI VE KURTARMA</small><h3>Canlı Sistem Sağlığı</h3></div></header><span><small>Demo REST</small><b>{status?.connected ? 'BAĞLI' : 'BEKLİYOR'}</b></span><span><small>Kullanıcı akışı</small><b>{v21?.stream.status || '—'}</b></span><span><small>Aktarım yolu</small><b>{v21?.stream.transport || '—'}</b></span><span><small>Akış hatası</small><b>{v21?.stream.error_count ?? 0}</b></span><span><small>Son yedek</small><b>{stamp(v21?.last_saved)}</b></span><div><button disabled={v21Busy} onClick={() => runDrill('RECONNECT')}>BAĞLANTI TATBİKATI</button><button disabled={v21Busy} onClick={() => runDrill('PROTECTION')}>STOP TATBİKATI</button><button disabled={v21Busy} onClick={() => runDrill('EMERGENCY')}>ACİL DURDURMA TATBİKATI</button></div></article></div>
      <div className="v21SafetyLock"><LockKeyhole/><span><b>GERÇEK PARA VE GERÇEK BINANCE EMİR KANALI FİZİKSEL OLARAK YOK</b><small>Bu paket yalnızca https://demo-fapi.binance.com ve wss://demo-fstream.binance.com adreslerini kullanır.</small></span><strong>DEMO ONLY</strong></div>
    </section>}
  </section>
}
