<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Box, Connection, Warning, ChatDotRound } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { login } from '@/api/auth'
import { ROLE_LABELS } from '@/types/role'
import type { RoleType } from '@/types/role'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const loading = ref(false)
const formRef = ref()

const form = reactive({
  username: '',
  password: '',
  role: 'logistics_admin' as RoleType,
})

const roleOptions: { value: RoleType; label: string }[] = [
  { value: 'system_admin', label: ROLE_LABELS.system_admin },
  { value: 'logistics_admin', label: ROLE_LABELS.logistics_admin },
  { value: 'warehouse_procurement', label: ROLE_LABELS.warehouse_procurement },
  { value: 'campus_supplier', label: ROLE_LABELS.campus_supplier },
  { value: 'counselor_teacher', label: ROLE_LABELS.counselor_teacher },
]

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const features = [
  { icon: Box, title: '全生命周期', desc: '采购→仓储→配送一体化' },
  { icon: Connection, title: '溯源可查', desc: '批次号追溯全链路' },
  { icon: Warning, title: '安全预警', desc: '临期短缺自动提醒' },
  { icon: ChatDotRound, title: 'AI 智能体', desc: '自然语言申请采购' },
]

function getDefaultRedirect(role: RoleType): string {
  switch (role) {
    case 'system_admin': return '/user'
    case 'counselor_teacher': return '/purchase/apply'
    case 'campus_supplier': return '/supplier/orders'
    default: return '/dashboard'
  }
}

async function handleLogin() {
  await formRef.value?.validate()
  loading.value = true
  try {
    const res: any = await login(form)
    const token = res?.access_token || res?.token || res?.data?.access_token
    const user = res?.user || res?.data?.user
    if (token) {
      const actualRole = (user?.role || form.role) as RoleType
      userStore.setToken(token)
      userStore.setUserInfo(user || { id: 1, username: form.username, real_name: '用户', role: actualRole })
      ElMessage.success('登录成功')
      const redirect = (route.query.redirect as string) || getDefaultRedirect(actualRole)
      router.push(redirect)
    } else {
      ElMessage.warning('演示模式：已选择角色登录')
      userStore.setToken('demo-token')
      userStore.setUserInfo({ id: 1, username: form.username, real_name: form.username, role: form.role })
      router.push(getDefaultRedirect(form.role))
    }
  } catch {
    ElMessage.warning('后端未启动，进入演示模式')
    userStore.setToken('demo-token')
    userStore.setUserInfo({ id: 1, username: form.username, real_name: form.username, role: form.role })
    router.push(getDefaultRedirect(form.role))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (userStore.isLoggedIn) {
    const role = userStore.userInfo?.role as RoleType
    router.replace(role ? getDefaultRedirect(role) : '/dashboard')
  }
})
</script>

<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="noise" aria-hidden="true" />
      <div class="grid-pattern" />
      <div class="orb orb-1" />
      <div class="orb orb-2" />
      <div class="orb orb-3" />
      <div class="floating-dots">
        <span v-for="i in 12" :key="i" class="dot" :style="`--i: ${i}; --x: ${(i % 4) * 25}%; --y: ${Math.floor(i / 4) * 33}%`" />
      </div>
    </div>

    <div class="login-layout">
      <!-- 左侧品牌区 -->
      <div class="brand-panel">
        <div class="brand-content">
          <div class="brand-logo">
            <span class="logo-icon">链</span>
            <span class="logo-text">供应链平台</span>
          </div>
          <h2 class="brand-title">校园物资供应链<br />安全健康监测平台</h2>
          <p class="brand-desc">—— 采购 · 仓储 · 配送 · 溯源 · AI 智能体 ——</p>

          <div class="features">
            <div
              v-for="(f, i) in features"
              :key="f.title"
              class="feature-item"
              :style="`--delay: ${i * 0.1}s`"
            >
              <div class="feature-icon">
                <el-icon :size="24"><component :is="f.icon" /></el-icon>
              </div>
              <div class="feature-text">
                <span class="feature-title">{{ f.title }}</span>
                <span class="feature-desc">{{ f.desc }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧登录区 -->
      <div class="form-panel">
        <div class="form-wrap">
          <div class="card-header">
            <h3>欢迎登录</h3>
            <p>请选择身份并输入账号密码</p>
          </div>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            class="login-form"
            size="large"
            @submit.prevent="handleLogin"
          >
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                placeholder="用户名"
                :prefix-icon="User"
                autocomplete="username"
              />
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码"
                show-password
                autocomplete="current-password"
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            <el-form-item prop="role">
              <el-select v-model="form.role" placeholder="选择角色" style="width: 100%">
                <el-option
                  v-for="opt in roleOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                class="submit-btn"
                :loading="loading"
                native-type="submit"
              >
                登 录
              </el-button>
            </el-form-item>
          </el-form>

          <p class="demo-hint">
            演示账号：system_admin、logistics_admin、warehouse_procurement、campus_supplier、counselor_teacher，密码均为
            <strong>123456</strong>（与后端 <code>init_db.py</code> 一致；首次部署请先在后端目录执行
            <code>python init_db.py</code>）
          </p>
          <p class="demo-hint demo-hint-tip">
            局域网访问：后端请用 <code>--host 0.0.0.0</code>；前端 <code>npm run dev</code> 已 <code>host: true</code>，内网段
            CORS 默认已放开。
          </p>
          <p class="demo-hint demo-hint-tip">多角色同时演示时，请为每个角色单独开「无痕/隐私窗口」登录，避免 token 互相覆盖</p>
          <router-link to="/upload" class="upload-link">匿名举报 / 反馈材料上传</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: stretch;
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: fixed;
  inset: 0;
  background: linear-gradient(135deg, #fafaf9 0%, #f5f5f4 50%, #e8e8ed 100%);
  z-index: 0;

  .noise {
    position: absolute;
    inset: 0;
    opacity: 0.04;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  }

  .grid-pattern {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(79, 70, 229, 0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(79, 70, 229, 0.04) 1px, transparent 1px);
    background-size: 32px 32px;
  }

  .orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(100px);
    opacity: 0.4;
    animation: floatOrb 25s ease-in-out infinite;
  }
  .orb-1 {
    width: 450px;
    height: 450px;
    background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
    top: -150px;
    left: 10%;
  }
  .orb-2 {
    width: 320px;
    height: 320px;
    background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
    bottom: -80px;
    left: 25%;
    animation-delay: 8s;
  }
  .orb-3 {
    width: 280px;
    height: 280px;
    background: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%);
    top: 40%;
    right: 15%;
    animation-delay: 15s;
  }

  .floating-dots {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }
  .dot {
    position: absolute;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgba(79, 70, 229, 0.15);
    left: var(--x);
    top: var(--y);
    animation: pulse 3s ease-in-out infinite;
    animation-delay: calc(var(--i) * 0.2s);
  }
}

@keyframes floatOrb {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(20px, -30px) scale(1.02); }
  66% { transform: translate(-15px, 20px) scale(0.98); }
}

@keyframes pulse {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.2); }
}

.login-layout {
  position: relative;
  z-index: 1;
  display: flex;
  width: 100%;
  min-height: 100vh;
}

.brand-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  max-width: 55%;
}

.brand-content {
  max-width: 480px;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 40px;

  .logo-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    background: var(--gradient-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 22px;
    font-weight: 700;
    color: #fff;
    box-shadow: 0 8px 24px rgba(79, 70, 229, 0.35);
  }

  .logo-text {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.brand-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.35;
  letter-spacing: -0.5px;
  margin: 0 0 16px;
}

.brand-desc {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0 0 48px;
  letter-spacing: 1px;
}

.features {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 14px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: all 0.3s ease;
  animation: slideIn 0.6s ease backwards;
  animation-delay: var(--delay);

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(79, 70, 229, 0.12);
    border-color: rgba(79, 70, 229, 0.2);
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
}

.feature-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--primary-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
  flex-shrink: 0;
}

.feature-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.feature-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.feature-desc {
  font-size: 13px;
  color: var(--text-secondary);
}

.form-panel {
  width: 480px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 20%;
    bottom: 20%;
    width: 1px;
    background: linear-gradient(to bottom, transparent, rgba(79, 70, 229, 0.15), transparent);
  }
}

.form-wrap {
  width: 100%;
  max-width: 360px;
}

.card-header {
  margin-bottom: 32px;

  h3 {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 8px;
    letter-spacing: -0.3px;
  }

  p {
    font-size: 14px;
    color: var(--text-muted);
    margin: 0;
  }
}

.login-form {
  :deep(.el-input__wrapper) {
    padding: 12px 16px;
    border-radius: 10px;
  }
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 10px !important;
}

.demo-hint {
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 20px;
}
.demo-hint-tip { margin-top: 6px; color: var(--primary); font-size: 11px; }
.upload-link { display: block; text-align: center; margin-top: 12px; font-size: 13px; color: var(--primary); }

@media (max-width: 1024px) {
  .login-layout {
    flex-direction: column;
  }

  .brand-panel {
    max-width: 100%;
    padding: 32px 24px;
  }

  .brand-title {
    font-size: 26px;
  }

  .features {
    grid-template-columns: 1fr;
  }

  .form-panel {
    width: 100%;

    &::before {
      left: 20%;
      right: 20%;
      top: 0;
      bottom: auto;
      height: 1px;
      width: auto;
      background: linear-gradient(to right, transparent, rgba(79, 70, 229, 0.15), transparent);
    }
  }
}
</style>
