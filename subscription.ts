export type BillingInterval = 'monthly'|'annual'
export type PlanCode = 'STARTER'|'PRO'|'ELITE'
export type Entitlements = {
  canUseDemoTrading:boolean
  canUseLiveTrading:boolean
  canUseAdvancedAnalytics:boolean
  canUseBacktesting:boolean
  canUseAdvancedAI:boolean
  maxActivePositions:number
}
export type SubscriptionPlan = {
  code:PlanCode
  name:string
  description:string
  monthlyPrice:number
  annualPrice:number
  features:string[]
  entitlements:Entitlements
}

export const SUBSCRIPTION_PLANS:SubscriptionPlan[] = [
  {code:'STARTER',name:'Starter',description:'A focused starting point for disciplined Demo trading.',monthlyPrice:19,annualPrice:190,features:['Demo trading access','Basic market analysis','Standard dashboard access','Basic trading intelligence','Limited bot usage','Limited active positions','Standard strategies'],entitlements:{canUseDemoTrading:true,canUseLiveTrading:false,canUseAdvancedAnalytics:false,canUseBacktesting:false,canUseAdvancedAI:false,maxActivePositions:1}},
  {code:'PRO',name:'Pro',description:'The complete workspace for active, risk-aware traders.',monthlyPrice:39,annualPrice:390,features:['Everything in Starter','Live trading access','Advanced risk management','Advanced market intelligence','More active positions','Trading automation','Advanced performance analytics','Advanced dashboard features'],entitlements:{canUseDemoTrading:true,canUseLiveTrading:true,canUseAdvancedAnalytics:true,canUseBacktesting:true,canUseAdvancedAI:false,maxActivePositions:3}},
  {code:'ELITE',name:'Elite',description:'Maximum intelligence, control and support for serious operation.',monthlyPrice:79,annualPrice:790,features:['Everything in Pro','Highest position limits','Advanced AI trading intelligence','Advanced backtesting','Advanced market analytics','Priority support','Early access to new features','Advanced risk controls'],entitlements:{canUseDemoTrading:true,canUseLiveTrading:true,canUseAdvancedAnalytics:true,canUseBacktesting:true,canUseAdvancedAI:true,maxActivePositions:5}},
]

export const PLAN_BY_CODE = Object.fromEntries(SUBSCRIPTION_PLANS.map(plan => [plan.code,plan])) as Record<PlanCode,SubscriptionPlan>
export const annualSavings = (plan:SubscriptionPlan) => plan.monthlyPrice * 12 - plan.annualPrice
export const subscriptionStatus = (subscription?:{status?:string;expires_at?:string|null;trial_end?:string|null}|null) => {
  if (!subscription) return 'FREE'
  const expiry = subscription.trial_end || subscription.expires_at
  if (expiry && new Date(expiry).getTime() <= Date.now()) return 'EXPIRED'
  return subscription.status === 'TRIAL' ? 'TRIAL' : subscription.status === 'ACTIVE' ? 'ACTIVE' : String(subscription.status || 'FREE')
}
