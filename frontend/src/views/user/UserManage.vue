<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listUsers, createUser } from '@/api/user'
import type { UserItem, UserCreateParams } from '@/api/user'
import { ROLE_LABELS } from '@/types/role'
import type { RoleType } from '@/types/role'

const loading = ref(false)
const tableData = ref<UserItem[]>([])
const dialogVisible = ref(false)
const submitLoading = ref(false)
const form = reactive<UserCreateParams & { passwordConfirm?: string }>({
  username: '',
  password: '',
  real_name: '',
  role: 'counselor_teacher',
  department: '',
  phone: '',
  passwordConfirm: '',
})

const roleOptions = Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }))

function resetForm() {
  form.username = ''
  form.password = ''
  form.real_name = ''
  form.role = 'counselor_teacher'
  form.department = ''
  form.phone = ''
  form.passwordConfirm = ''
}

async function fetchData() {
  loading.value = true
  try {
    const res: any = await listUsers()
    tableData.value = Array.isArray(res) ? res : res?.data ?? []
  } catch {
    tableData.value = []
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  resetForm()
  dialogVisible.value = true
}

async function handleCreate() {
  if (!form.username?.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (!form.password) {
    ElMessage.warning('请输入密码')
    return
  }
  if (form.password.length < 6) {
    ElMessage.warning('密码至少 6 位')
    return
  }
  if (form.password !== form.passwordConfirm) {
    ElMessage.warning('两次密码输入不一致')
    return
  }
  submitLoading.value = true
  try {
    await createUser({
      username: form.username.trim(),
      password: form.password,
      real_name: form.real_name?.trim() || undefined,
      role: form.role,
      department: form.department?.trim() || undefined,
      phone: form.phone?.trim() || undefined,
    })
    ElMessage.success('添加成功')
    dialogVisible.value = false
    fetchData()
  } finally {
    submitLoading.value = false
  }
}

function getRoleLabel(role: string) {
  return ROLE_LABELS[role as RoleType] ?? role
}

onMounted(fetchData)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="openAddDialog">新增用户</el-button>
    </div>
    <div class="table-card">
      <el-table :data="tableData" v-loading="loading" style="width: 100%">
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="real_name" label="姓名" />
        <el-table-column prop="role" label="角色" width="140">
          <template #default="{ row }">{{ getRoleLabel(row.role) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" />
      </el-table>
    </div>

    <el-dialog v-model="dialogVisible" title="新增用户" width="420px" :close-on-click-modal="false" @close="resetForm">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="form.password" type="password" placeholder="至少 6 位" show-password />
        </el-form-item>
        <el-form-item label="确认密码" required>
          <el-input v-model="form.passwordConfirm" type="password" placeholder="再次输入密码" show-password />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.real_name" placeholder="选填" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="form.role" placeholder="选择角色" style="width: 100%">
            <el-option v-for="opt in roleOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="form.department" placeholder="选填" />
        </el-form-item>
        <el-form-item label="手机">
          <el-input v-model="form.phone" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; margin-bottom: 20px; }
.table-card { padding: 20px; background: var(--bg-card); border-radius: 12px; }
</style>
