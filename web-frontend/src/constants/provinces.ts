export const provinceOptions = [
  '北京', '天津', '河北', '山西', '内蒙古',
  '辽宁', '吉林', '黑龙江',
  '上海', '江苏', '浙江', '安徽', '福建', '江西', '山东',
  '河南', '湖北', '湖南', '广东', '广西', '海南',
  '重庆', '四川', '贵州', '云南', '西藏',
  '陕西', '甘肃', '青海', '宁夏', '新疆',
  '香港', '澳门', '台湾',
]

/** 电站配置使用的省份选项（拼音 value + 中文 label），与后端 Province Literal 保持同步 */
export const stationProvinceOptions = [
  { label: '甘肃', value: 'gansu' },
  { label: '青海', value: 'qinghai' },
  { label: '宁夏', value: 'ningxia' },
  { label: '新疆', value: 'xinjiang' },
  { label: '内蒙古', value: 'neimenggu' },
  { label: '河北', value: 'hebei' },
  { label: '山东', value: 'shandong' },
  { label: '广东', value: 'guangdong' },
  { label: '云南', value: 'yunnan' },
  { label: '四川', value: 'sichuan' },
  { label: '山西', value: 'shanxi' },
  { label: '江苏', value: 'jiangsu' },
  { label: '辽宁', value: 'liaoning' },
  { label: '吉林', value: 'jilin' },
  { label: '黑龙江', value: 'heilongjiang' },
  { label: '河南', value: 'henan' },
  { label: '湖北', value: 'hubei' },
  { label: '湖南', value: 'hunan' },
  { label: '安徽', value: 'anhui' },
  { label: '福建', value: 'fujian' },
  { label: '浙江', value: 'zhejiang' },
  { label: '江西', value: 'jiangxi' },
  { label: '贵州', value: 'guizhou' },
  { label: '西藏', value: 'xizang' },
  { label: '海南', value: 'hainan' },
  { label: '广西', value: 'guangxi' },
  { label: '重庆', value: 'chongqing' },
  { label: '北京', value: 'beijing' },
  { label: '天津', value: 'tianjin' },
  { label: '上海', value: 'shanghai' },
  { label: '陕西', value: 'shaanxi' },
] as const

/** 拼音 → 中文映射 */
export const provinceLabels: Record<string, string> = Object.fromEntries(
  stationProvinceOptions.map((p) => [p.value, p.label]),
)
