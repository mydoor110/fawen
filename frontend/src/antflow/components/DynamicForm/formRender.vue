<template>
    <div>
      <v-form-render :form-json="formJson" :form-data="formData" :option-data="optionData" ref="vFormRef">
      </v-form-render>
    </div>
  </template>
  
  <script setup>
    import { ref, reactive } from 'vue'
    import { ElMessage } from 'element-plus'
  
    /* 公文审批表单模板 */
    const formJson = reactive({"widgetList":[{"key":95698,"type":"grid","category":"container","icon":"grid","cols":[{"type":"grid-col","category":"container","icon":"grid-col","internal":true,"widgetList":[{"key":71081,"type":"input","icon":"text-field","formItemFlag":true,"options":{"name":"docTitle","label":"公文标题","labelAlign":"","type":"text","defaultValue":"","placeholder":"请输入公文标题","columnWidth":"200px","size":"","labelWidth":null,"labelHidden":false,"readonly":true,"disabled":false,"hidden":false,"clearable":true,"showPassword":false,"required":true,"requiredHint":"","validation":"","validationHint":"","customClass":"","labelIconClass":null,"labelIconPosition":"rear","labelTooltip":null,"minLength":null,"maxLength":null,"showWordLimit":false,"prefixIcon":"","suffixIcon":"","appendButton":false,"appendButtonDisabled":false,"buttonIcon":"custom-search","onCreated":"","onMounted":"","onInput":"","onChange":"","onFocus":"","onBlur":"","onValidate":"","onAppendButtonClick":""},"id":"docTitle"}],"options":{"name":"gridCol15100","hidden":false,"span":12,"offset":0,"push":0,"pull":0,"responsive":false,"md":12,"sm":12,"xs":12,"customClass":""},"id":"grid-col-15100"},{"type":"grid-col","category":"container","icon":"grid-col","internal":true,"widgetList":[{"key":71082,"type":"select","icon":"select-field","formItemFlag":true,"options":{"name":"docType","label":"公文文种","labelAlign":"","defaultValue":"","placeholder":"请选择公文文种","columnWidth":"200px","size":"","labelWidth":null,"labelHidden":false,"disabled":false,"hidden":false,"clearable":true,"required":true,"requiredHint":"","validation":"","validationHint":"","customClass":"","labelIconClass":null,"labelIconPosition":"rear","labelTooltip":null,"optionItems":[{"label":"通知","value":"通知"},{"label":"报告","value":"报告"},{"label":"请示","value":"请示"},{"label":"批复","value":"批复"},{"label":"函","value":"函"},{"label":"纪要","value":"纪要"},{"label":"决定","value":"决定"},{"label":"意见","value":"意见"}],"fieldTypeName":"select","fieldType":"1"},"id":"docType"}],"options":{"name":"gridCol47087","hidden":false,"span":12,"offset":0,"push":0,"pull":0,"responsive":false,"md":12,"sm":12,"xs":12,"customClass":""},"id":"grid-col-47087"}],"options":{"name":"grid98540","hidden":false,"gutter":12,"colHeight":null,"customClass":""},"id":"grid98540"}],"formConfig":{"modelName":"formData","refName":"vForm","rulesName":"rules","labelWidth":80,"labelPosition":"left","size":"","labelAlign":"label-left-align","cssCode":"","customClass":[],"functions":"","layoutType":"PC","jsonVersion":3,"onFormCreated":"","onFormMounted":"","onFormDataChange":""}})
    const formData = reactive({})
    const optionData = reactive({})
    const vFormRef = ref(null)
  
    const submitForm = () => {
      vFormRef.value.getFormData().then(formData => {
        alert( JSON.stringify(formData) )
      }).catch(error => {
        ElMessage.error(error)
      })
    }
  </script>