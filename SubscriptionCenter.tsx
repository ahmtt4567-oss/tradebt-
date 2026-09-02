import { useEffect, useState } from 'react'
import { ArrowRight, Check, CreditCard, LockKeyhole, RefreshCw, ShieldCheck, Sparkles } from 'lucide-react'
import { API_BASE } from './api'
import { annualSavings, PLAN_BY_CODE, SUBSCRIPTION_PLANS, type BillingInterval, type PlanCode } from './subscription'

const SESSION_KEYS = ['protrebot-v25-session','protrebot-v24-session','protrebot-v23-session','protrebot-v22-session']
type License = {plan?:PlanCode;status?:string;expires_at?:string|null;starts_at?:string|null}
type SubscriptionView = {status:string;plan:PlanCode|null;billingInterval:BillingInterval|null;trialStart:string|null;trialEnd:string|null;currentPeriodEnd:string|null;currentPrice:number|null;features:string[];cancelAtPeriodEnd:boolean;mode:'DEVELOPMENT'|'STRIPE'}
const token = () => SESSION_KEYS.map(key => localStorage.getItem(key) || sessionStorage.getItem(key)).find(Boolean) || ''
const date = (value?:string|null) => value ? new Date(value).toLocaleDateString('en-US',{year:'numeric',month:'short',day:'numeric'}) : 'Unavailable'
const daysLeft = (value?:string|null) => value ? Math.max(0,Math.ceil((new Date(value).getTime() - Date.now()) / 86400000)) : 0

export default function SubscriptionCenter({mode,onNavigate}:{mode:'pricing'|'billing';onNavigate:(target:'pricing'|'billing'|'live')=>void}) {
  const [interval,setInterval] = useState<BillingInterval>('monthly')
  const [subscription,setSubscription] = useState<SubscriptionView|null>(null)
  const [busy,setBusy] = useState(false)
  const [notice,setNotice] = useState('')
  const [error,setError] = useState('')
  const currentToken = token()

  useEffect(() => {
    if (!currentToken) return
    fetch(`${API_BASE}/v22/subscription`,{headers:{Authorization:`Bearer ${currentToken}`}}).then(async response => {
      if (!response.ok) throw new Error('Subscription status unavailable')
      setSubscription(await response.json() as SubscriptionView)
    }).catch(() => setSubscription(null))
  },[currentToken])

  const startTrial = async () => {
    if (!currentToken) { setNotice('Sign in through the existing account workspace to start your trial.'); onNavigate('live'); return }
    setBusy(true);setError('');setNotice('')
    try {
      const response = await fetch(`${API_BASE}/v22/subscription/trial`,{method:'POST',headers:{Authorization:`Bearer ${currentToken}`,'Content-Type':'application/json'}})
      const payload = await response.json().catch(() => null) as {detail?:string}|SubscriptionView|null
      if (!response.ok) throw new Error(payload && 'detail' in payload ? payload.detail : 'Trial could not be started')
      setSubscription(payload as SubscriptionView);setNotice('Your 7-day free trial is active.')
    } catch (value) { setError(value instanceof Error ? value.message : 'Trial could not be started.') }
    finally { setBusy(false) }
  }

  const requestPlan = async (plan:PlanCode) => {
    if (!currentToken) { setNotice('Sign in through the existing account workspace to choose a plan.'); onNavigate('live'); return }
    setBusy(true);setError('');setNotice('')
    try {
      const response = await fetch(`${API_BASE}/v22/subscription/checkout`,{method:'POST',headers:{Authorization:`Bearer ${currentToken}`,'Content-Type':'application/json'},body:JSON.stringify({plan,billing_interval:interval})})
      const payload = await response.json().catch(() => null) as {detail?:string;message?:string}|null
      if (!response.ok) throw new Error(payload?.detail || 'Checkout is unavailable')
      setNotice(payload?.message || 'Development billing mode: Stripe Checkout is not configured yet.')
    } catch (value) { setError(value instanceof Error ? value.message : 'Checkout is unavailable.') }
    finally { setBusy(false) }
  }

  const cancelSubscription = async () => {
    if (!currentToken) { setNotice('Sign in through the existing account workspace to manage cancellation.'); onNavigate('live'); return }
    setBusy(true);setError('');setNotice('')
    try {
      const response = await fetch(`${API_BASE}/v22/subscription/cancel`,{method:'POST',headers:{Authorization:`Bearer ${currentToken}`}})
      const payload = await response.json().catch(() => null) as {detail?:string}|SubscriptionView|null
      if (!response.ok) throw new Error(payload && 'detail' in payload ? payload.detail : 'Cancellation could not be scheduled')
      setSubscription(payload as SubscriptionView);setNotice('Cancellation is scheduled for the end of the current period.')
    } catch (value) { setError(value instanceof Error ? value.message : 'Cancellation could not be scheduled.') }
    finally { setBusy(false) }
  }

  if (mode === 'billing') return <main className="subscriptionPage subscriptionBilling"><header className="subscriptionPageHeader"><div><span>PROTREBOT BILLING</span><h1>Subscription control center</h1><p>Manage access, trial status and billing readiness in one place.</p></div><button onClick={() => onNavigate('pricing')}><Sparkles/>VIEW PLANS</button></header><section className="subscriptionStatusCard"><div className="subscriptionStatusTop"><span><small>STATUS</small><strong className={`subscriptionStatus subscriptionStatus-${(subscription?.status || 'FREE').toLowerCase()}`}>{subscription?.status || 'FREE'}</strong></span><span><small>CURRENT PLAN</small><b>{subscription?.plan || 'No active plan'}</b></span><span><small>CURRENT PRICE</small><b>{subscription?.currentPrice === null || subscription?.currentPrice === undefined ? '—' : `$${subscription.currentPrice}`}</b></span><span><small>NEXT BILLING DATE</small><b>{date(subscription?.currentPeriodEnd)}</b></span></div><div className="subscriptionTrialBar"><div><small>TRIAL STATUS</small><b>{subscription?.status === 'TRIAL' ? `${daysLeft(subscription.trialEnd)} days remaining` : 'No active trial'}</b></div><span>{subscription?.trialEnd ? `Expires ${date(subscription.trialEnd)}` : 'Start a 7-day free trial when eligible.'}</span></div><div className="subscriptionFeatureList">{(subscription?.features || ['Read-only dashboard access','Account data is preserved','Billing status is unavailable until an account is connected.']).map(feature => <span key={feature}><Check/>{feature}</span>)}</div></section><section className="subscriptionBillingActions"><button onClick={startTrial} disabled={busy}><RefreshCw/>START 7-DAY FREE TRIAL</button><button onClick={() => onNavigate('pricing')}><Sparkles/>UPGRADE OR DOWNGRADE</button><button onClick={cancelSubscription} disabled={busy}><CreditCard/>CANCEL AT PERIOD END</button><button onClick={() => setNotice('Development billing mode: customer portal is not configured yet.')}><CreditCard/>MANAGE BILLING</button><div className="subscriptionNotice">{notice || 'Stripe billing is prepared but not configured. No payment is collected in development mode.'}{error && <b>{error}</b>}</div></section></main>

  return <main className="subscriptionPage subscriptionPricing"><header className="subscriptionPageHeader"><div><span>PROTREBOT · TRADING INTELLIGENCE PLATFORM</span><h1>Choose the workspace that matches your operation.</h1><p>Start with a 7-day trial. Upgrade when your process is ready. Your data stays yours.</p></div><button onClick={() => onNavigate('billing')}><CreditCard/>BILLING</button></header><div className="subscriptionModeSwitch"><button className={interval === 'monthly' ? 'active' : ''} onClick={() => setInterval('monthly')}>MONTHLY</button><button className={interval === 'annual' ? 'active' : ''} onClick={() => setInterval('annual')}>ANNUAL <small>SAVE UP TO 17%</small></button></div><section className="subscriptionPlans">{SUBSCRIPTION_PLANS.map(plan => { const price = interval === 'monthly' ? plan.monthlyPrice : plan.annualPrice; return <article className={`subscriptionPlan ${plan.code === 'PRO' ? 'subscriptionPlanPopular' : ''}`} key={plan.code}>{plan.code === 'PRO' && <div className="subscriptionPopular">MOST POPULAR</div>}<header><span>{plan.code}</span><h2>{plan.name}</h2><p>{plan.description}</p></header><div className="subscriptionPrice"><strong>${price}</strong><span>/{interval === 'monthly' ? 'month' : 'year'}</span></div>{interval === 'annual' && <small className="subscriptionSavings">Save ${annualSavings(plan)} per year</small>}<ul>{plan.features.map(feature => <li key={feature}><Check/>{feature}</li>)}</ul><button onClick={() => requestPlan(plan.code)} disabled={busy}>{currentToken && subscription?.plan === plan.code ? 'CURRENT PLAN' : `START ${plan.name.toUpperCase()}`}<ArrowRight/></button>{!currentToken && plan.code === 'STARTER' && <button className="subscriptionTrialCta" onClick={startTrial}>START 7-DAY FREE TRIAL</button>}</article> })}</section><div className="subscriptionDevelopment"><LockKeyhole/><span><b>DEVELOPMENT BILLING MODE</b><small>Stripe Checkout, subscriptions, webhooks and the customer portal are prepared but payment collection is disabled until server credentials are configured.</small></span><ShieldCheck/></div>{notice && <p className="subscriptionFeedback">{notice}</p>}{error && <p className="subscriptionFeedback subscriptionFeedbackError">{error}</p>}</main>
}
