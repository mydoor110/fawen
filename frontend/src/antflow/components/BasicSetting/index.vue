<template>
    <div class="my-nav-content">
        <div class="form-container">
            <el-form ref="ruleFormRef" :model="form" :rules="rules" label-width="auto"
                style="max-width: 600px;margin: auto;">
                <el-form-item label="流程编号" prop="formCode">
                    <el-input v-model="form.formCode" disabled placeholder="自动生成" :style="{ width: '100%' }" />
                </el-form-item>
                <el-form-item label="流程名称" prop="bpmnName">
                    <el-input v-model="form.bpmnName" placeholder="请输入流程名称，如：标准公文审批流程" :style="{ width: '100%' }" />
                </el-form-item>
                <el-form-item label="流程说明" prop="remark">
                    <el-input v-model="form.remark" type="textarea" placeholder="请输入流程说明" :maxlength="200"
                        show-word-limit :autosize="{ minRows: 3, maxRows: 6 }" :style="{ width: '100%' }"></el-input>
                </el-form-item>
            </el-form>
        </div>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted, getCurrentInstance } from 'vue'
import { NodeUtils } from '@/antflow/utils/nodeUtils'
const { proxy } = getCurrentInstance()
const emit = defineEmits(['nextChange'])
let props = defineProps({
    basicData: {
        type: Object,
        default: () => (null),
    }
});

const generatorID = "DOC_" + NodeUtils.idGenerator();
const ruleFormRef = ref(null);

const form = reactive({
    bpmnName: '公文审批流程',
    bpmnCode: generatorID,
    bpmnType: null,
    flowGroup: 1,
    formCode: generatorID,
    remark: '',
    effectiveStatus: true,
    deduplicationType: 1
})

onMounted(async () => {
    if (props.basicData) {
        form.bpmnName = props.basicData.bpmnName;
        form.bpmnCode = generatorID;
        form.bpmnType = props.basicData.bpmnType;
        form.formCode = props.basicData.formCode || generatorID;
        form.remark = props.basicData.remark;
        form.effectiveStatus = props.basicData.effectiveStatus;
        form.deduplicationType = props.basicData.deduplicationType;
    }
});

let rules = {
    bpmnName: [{
        required: true,
        message: '请输入流程名称',
        trigger: 'blur'
    }],
};

const nextSubmit = (ruleFormRef) => {
    if (!ruleFormRef) return
    ruleFormRef.validate((valid, fields) => {
        if (valid) {
            emit('nextChange', { label: "流程设计", key: "processDesign" })
        }
    })
}

// 给父级页面提供得获取本页数据得方法
const getData = () => {
    return new Promise((resolve, reject) => {
        proxy.$refs['ruleFormRef'].validate((valid, fields) => {
            if (!valid) {
                emit('nextChange', { label: "基础设置", key: "basicSettingDesign" })
                return;
            }
            form.effectiveStatus = form.effectiveStatus ? 1 : 0;
            resolve({ formData: form })
        })
    })
};
defineExpose({
    getData
})
</script>
<style lang="css" scoped>
.form-container {
    padding: 40px 20px;
}
</style>