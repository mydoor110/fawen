<template>
    <div class="my-nav">
        <div class="my-nav-left">
            <div class="my-nav-back">
                <i class="flowicon flowicon-left"></i>
            </div>
            <div class="my-nav-title">{{ title }}</div>
        </div>
        <div class="my-nav-center">
            <div class="step-tab">
                <div v-for="(item, index) in steps" :key="index" class="step"
                    :class="[activeStep == item.key ? 'active' : '']" @click="changeSteps(item)">
                    <span class="step-index">{{ index + 1 }}</span>
                    {{ item.label }}
                </div>
                <div class="ghost-step step" :style="{ transform: translateX }"></div>
            </div>
        </div>
        <div class="my-nav-right">
            <button type="button" class="flow-btn button-publish" @click="publish">
                <span>发 布</span>
            </button>
        </div>
    </div>
    <div v-if="processConfig" v-show="activeStep === 'basicSettingDesign'">
        <basicSetting ref="basicSettingDesign" :basicData="processConfig" @nextChange="changeSteps" />
    </div>
    <div v-if="nodeConfig" v-show="activeStep === 'processDesign'">
        <Process ref="processDesign" :processData="nodeConfig" @nextChange="changeSteps" />
    </div>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import { ElMessage } from 'element-plus';
import { FormatUtils } from '@/antflow/utils/formatcommit_data';
import { NodeUtils } from '@/antflow/utils/nodeUtils';
import { setWorkFlowData } from '@/antflow/api';
import { FormatDisplayUtils } from '@/antflow/utils/formatdisplay_data';
import { showLoading, closeLoading } from '@/antflow/utils/loading';
const basicSettingDesign = ref(null);
const processDesign = ref(null);
let activeStep = ref("basicSettingDesign"); // 激活的步骤面板
let steps = ref([
    { label: "基础设置", key: "basicSettingDesign" },
    { label: "流程设计", key: "processDesign" },
]);
let translateX = computed({
    get() {
        return `translateX(${(steps.value.findIndex(t => t.key === activeStep.value) - 1) * 100}%)`
    }
})
const changeSteps = (item) => {
    activeStep.value = item.key;
};
let processConfig = ref(null);
let nodeConfig = ref(null);
let title = ref('');
onMounted(async () => {
    showLoading();
    let mockjson = NodeUtils.createStartNode();
    let data = FormatDisplayUtils.getToTree(mockjson.data);
    processConfig.value = data;
    title.value = data.bpmnName;
    nodeConfig.value = data.nodeConfig;
    closeLoading();
});

const publish = () => {
    const step1 = basicSettingDesign.value.getData();
    const step2 = processDesign.value.getData();
    Promise.all([step1, step2])
        .then((res) => {
            let basicData = res[0].formData;
            var nodes = FormatUtils.formatSettings(res[1].formData); 
            Object.assign(basicData, { nodes: nodes });
            return basicData;
        })
        .then((data) => {
            console.log("流程数据:", JSON.stringify(data));
            setWorkFlowData(data).then((resLog) => {
                if (resLog.code == 200) { 
                    ElMessage.success("流程设置成功"); 
                } else {
                    ElMessage.error("流程设置失败");
                } 
            });
        })
        .catch((err) => {
            if (err) {
                console.log("设置失败" + JSON.stringify(err.msg));
                ElMessage.error("至少配置一个有效审批人节点");
            }
        });
};

</script>
<style lang="css" scoped>
.step-tab {
    display: flex;
    justify-content: center;
    position: relative;
    height: 60px;
    font-size: 14px;
    border-right: 0px solid #1583f2;
    text-align: center;
    cursor: pointer;
}

.step {
    width: 140px;
    line-height: 100%;
    padding-left: 30px;
    padding-right: 30px;
    line-height: 60px;
    cursor: pointer;
    position: relative;
}

.step-index {
    display: inline-block;
    width: 18px;
    height: 18px;
    border: 1px solid #fff;
    border-radius: 8px;
    line-height: 18px;
    text-align: center;
    box-sizing: border-box;
}

.ghost-step {
    position: absolute;
    height: 60px;
    z-index: -1;
    background: #4483f2;
    transition: transform .5s;
}

.ghost-step::after {
    content: '';
    border-width: 6px 6px 6px;
    border-style: solid;
    border-color: transparent transparent white;
    position: absolute;
    bottom: 0;
    left: 50%;
    margin-left: -6px;
}
</style>