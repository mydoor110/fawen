import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import App from './App.vue'
import router from './router'
import './styles/index.css'

const app = createApp(App)
const pinia = createPinia()

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 注册 AntFlow 全局组件（递归组件需要全局注册）
import addNode from '@/antflow/components/addNode.vue'
import nodeWrap from '@/antflow/components/nodeWrap.vue'
import $func from '@/antflow/utils/index'
app.component('nodeWrap', nodeWrap)
app.component('addNode', addNode)

// 注册 AntFlow 需要的全局指令和属性
app.directive('focus', { mounted: (el) => el.querySelector('input')?.focus() || el.focus?.() })
app.config.globalProperties.$func = $func

app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')
