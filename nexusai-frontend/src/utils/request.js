import axios from 'axios'
import { message } from 'ant-design-vue'

const request = axios.create({
  baseURL: '/api',
  timeout: 120000
})

request.interceptors.response.use(
  res => res.data,
  err => {
    message.error(`请求失败: ${err.message}`)
    return Promise.reject(err)
  }
)

export default request
