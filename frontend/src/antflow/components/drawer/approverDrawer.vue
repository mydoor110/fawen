<template>
    <el-drawer :append-to-body="true" title="审批人" v-model="visible" class="set_approver" :with-header="false"
        :show-close="false" :size="550" :before-close="saveApprover">
        <div class="el-drawer__header" style="border-bottom: 1px solid rgba(220, 220, 220, 1);">
            <span class="drawer-title">审批人</span>
        </div>
        <el-tabs v-model="activeName" class="set-tabs" @tab-click="handleTabClick">
            <el-tab-pane label="基础设置" name="baseTab">
                <span class="approver_content-title">💁设置审批人</span>
                <div class="approver_content">
                    <el-radio-group v-model="approverConfig.setType" class="clear" @change="changeType">
                        <el-radio v-for="({ value, label }) in setTypes" :key="value" :value="value">{{ label
                            }}</el-radio>
                    </el-radio-group>

                    <div class="approver_btn" v-if="approverConfig.setType == 1">
                        <el-button type="primary" @click="addApprover">添加/修改成员</el-button>
                        <p class="selected_list">
                            <span v-for="(item, index) in approverConfig.nodeApproveList" :key="index">🙍‍♂️{{ item.name
                                }}
                                <img src="@/antflow/assets/images/add-close1.png"
                                    @click="$func.removeEle(approverConfig.nodeApproveList, item, 'targetId')">
                            </span>
                            <a v-if="approverConfig.nodeApproveList.length != 0"
                                @click="approverConfig.nodeApproveList = []">清除</a>
                        </p>
                    </div>
                    <div class="approver_btn" v-show="approverConfig.setType == 3">
                        <el-button type="primary" @click="addRoleApprover">添加/修改审批角色</el-button>
                        <p class="selected_list">
                            <span v-for="(item, index) in approverConfig.nodeApproveList" :key="index">{{ item.name
                                }}
                                <img src="@/antflow/assets/images/add-close1.png"
                                    @click="$func.removeEle(approverConfig.nodeApproveList, item, 'targetId')">
                            </span>
                            <a v-if="approverConfig.nodeApproveList.length != 0"
                                @click="approverConfig.nodeApproveList = []">清除</a>
                        </p>
                    </div>
                    <div class="approver_text" v-if="approverConfig.setType == 5">
                        <p>该审批节点设置"发起人自己"后，审批人默认为发起人</p>
                    </div>
                </div>
                <div class="approver_block">
                    <p>✍多人审批时采用的审批方式</p>
                    <el-radio-group v-model="approverConfig.signType" class="clear">
                        <el-radio :value="1">会签（需所有审批人同意，不限顺序）</el-radio>
                        <br />
                        <el-radio :value="2">或签（只需一名审批人同意或拒绝即可）</el-radio>
                    </el-radio-group>
                </div>
                <div class="approver_block">
                    <p>✍审批人为空时</p>
                    <el-radio-group v-model="approverConfig.noHeaderAction" class="clear">
                        <el-radio :value="1">自动审批通过/不允许发起</el-radio>
                        <br />
                        <el-radio :value="2">转交给审核管理员</el-radio>
                    </el-radio-group>
                </div>
            </el-tab-pane>
            <el-tab-pane label="按钮设置" name="btnTab">
                <div class="approver_block">
                    <p>🚩审批页面按钮权限显示控制</p>
                    <el-checkbox v-model="checkedOk" label="同意" border
                        style="margin: 6px 0;width: 100%;height: 45px;" />
                    <el-checkbox v-model="checkedNot" label="不同意" border
                        style="margin: 6px 0;width: 100%;height: 45px;" />
                    <el-checkbox v-model="checkedBack" label="打回" border
                        style="margin: 6px 0;width: 100%;height: 45px;" />
                </div>
            </el-tab-pane>
        </el-tabs>
        <div class="flow-drawer__footer clear">
            <el-button type="primary" @click="saveApprover">确 定</el-button>
            <el-button @click="closeDrawer">取 消</el-button>
        </div>
        <selectUser v-model:visible="approverVisible" :data="checkedList" @change="sureApprover" />
        <role-dialog v-model:visible="approverRoleVisible" :data="checkedRoleList" @change="sureRoleApprover" />
    </el-drawer>
</template>
<script setup>
import { ref, watch, computed } from 'vue'
import $func from '@/antflow/utils/index'
import { setTypes } from '@/antflow/utils/const'
import { useStore } from '@/antflow/store'
import selectUser from '../dialog/selectUserDialog.vue'
import roleDialog from '../dialog/selectRoleDialog.vue'

let props = defineProps({
    directorMaxLevel: {
        type: Number,
        default: 0
    }
});
let approverConfig = ref({})
let approverVisible = ref(false)
let approverRoleVisible = ref(false)
let checkedRoleList = ref([])
let checkedList = ref([])
let store = useStore()
let { setApproverConfig, setApprover } = store
let approverConfig1 = computed(() => store.approverConfig1)
let approverDrawer = computed(() => store.approverDrawer)
let visible = computed({
    get() {
        return approverDrawer.value
    },
    set() {
        closeDrawer()
    }
})
let checkedOk = ref(true)
let checkedNot = ref(true)
let checkedBack = ref(false)
const activeName = ref('baseTab')

const handleTabClick = (tab, event) => {
    //console.log(tab, event)
}
watch(approverConfig1, (val) => {
    approverConfig.value = val.value || {}
    if (!approverConfig.value.nodeApproveList) {
        approverConfig.value.nodeApproveList = []
    }
})

const changeType = (val) => {
    approverConfig.value.nodeApproveList = [];
    approverConfig.value.signType = 1;
    approverConfig.value.noHeaderAction = 2;
}
const addApprover = () => {
    approverVisible.value = true;
    checkedList.value = approverConfig.value.nodeApproveList
}
const addRoleApprover = () => {
    approverRoleVisible.value = true;
    checkedRoleList.value = approverConfig.value.nodeApproveList
}
const sureApprover = (data) => {
    approverConfig.value.nodeApproveList = data;
    approverVisible.value = false;
}
const sureRoleApprover = (data) => {
    approverConfig.value.nodeApproveList = data;
    approverRoleVisible.value = false;
}
const saveApprover = () => {
    console.log('[ApproverDrawer] saveApprover called, setType:', approverConfig.value.setType, 'nodeApproveList:', JSON.stringify(approverConfig.value.nodeApproveList))
    approverConfig.value.error = !$func.setApproverStr(approverConfig.value)
    console.log('[ApproverDrawer] after setApproverStr, error:', approverConfig.value.error)
    setApproverConfig({
        value: approverConfig.value,
        flag: true,
        id: approverConfig1.value.id
    })
    closeDrawer()
}
const closeDrawer = () => {
    setApprover(false)
}
</script>
<style lang="css" scoped>
.el-tabs {
    margin-left: 20px !important;
    margin-right: 20px !important;
    height: calc(100% - 110px);
}

.selected_list {
    margin-bottom: 20px;
    line-height: 35px;
}

.selected_list span {
    margin-right: 10px;
    padding: 3px 6px 3px 9px;
    line-height: 12px;
    white-space: nowrap;
    border-radius: 5px;
    border: 1px solid rgba(220, 220, 220, 1);
}

.selected_list img {
    margin-left: 5px;
    width: 7px;
    height: 7px;
    cursor: pointer;
}

.approver_content {
    padding: 20px 20px 0; 
    border-bottom: 1px solid #f2f2f2;
    min-height: 200px;
    overflow: hidden;
    margin-bottom: 20px;
    border: 1px solid var(--el-border-color);
    border-bottom-left-radius: 5px;
    border-bottom-right-radius: 5px;
}

.approver_content-title {
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    display: inline-block;
    padding: 5px;
    width: 100%;
    background-color: var(--el-border-color);
}

.approver_btn,
.approver_content {
    .el-button {
        margin-bottom: 20px;
    }
}

.approver_content,
.approver_block,
.approver_btn {
    .el-radio-group {
        display: unset;
    } 
    .el-radio {
        width: 45%;
        margin-bottom: 20px;
        height: 16px;
    }
}

.approver_text {
    padding: 10px 0px;
    color: #f8642d;
} 

.approver_block p {
    line-height: 19px;
    font-size: 15px;
    margin-bottom: 14px;
    font-weight: 600;
}

</style>