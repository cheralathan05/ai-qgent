import api from './client';
import type { DeviceInfo } from '../apa/types';

export type PairingStep =
  | 'idle'
  | 'discovering'
  | 'connecting'
  | 'verifying'
  | 'trusting'
  | 'permissions'
  | 'registering'
  | 'twin_creating'
  | 'ready'
  | 'error';

export interface USBDeviceInfo {
  serial: string;
  manufacturer: string;
  brand: string;
  model: string;
  android_version: string;
  sdk_version: number;
  build_number: string;
  battery_percentage: number;
  charging: boolean;
  screen_width: number;
  screen_height: number;
  cpu_abi: string;
  ram_total_kb: number;
  storage_total_bytes: number;
  foreground_app: string;
  screen_on: boolean;
  lock_state: string;
  usb_debugging: boolean;
  developer_options: boolean;
  accessibility_service: boolean;
  device_name: string;
  adb_authorized: boolean;
  connection_quality: string;
  already_registered?: boolean;
  device_id?: string;
}

export interface PairingStatus {
  success: boolean;
  user_id?: string;
  workflow_state: PairingStep;
  has_active_session: boolean;
  active_session: {
    id: string;
    state: string;
    serial: string;
    manufacturer: string;
    model: string;
    device_id: string;
    error_message: string;
  } | null;
  paired: boolean;
  trusted: boolean;
  trusted_count: number;
  device_count: number;
  usb_connected_count: number;
  usb_devices: { serial: string; state: string }[];
  devices: DeviceInfo[];
}

export interface DeviceTwin {
  id: string;
  device_id: string;
  manufacturer: string;
  model: string;
  brand: string;
  android_version: string;
  sdk_version: number;
  build_number: string;
  cpu_abi: string;
  ram_total_gb: number;
  storage_total_gb: number;
  screen_width: number;
  screen_height: number;
  screen_density: number;
  installed_apps_count: number;
  capabilities: string[];
  permissions: Record<string, string>;
  health_score: number;
  trust_score: number;
  readiness_score: number;
  ai_ready: boolean;
  sync_state: string;
  last_sync_at: string | null;
  last_seen: string | null;
}

export interface HeartbeatData {
  battery_level: number;
  battery_charging: boolean;
  foreground_app: string;
  foreground_package: string;
  current_activity: string;
  screen_state: string;
  lock_state: string;
  network_type: string;
  network_strength: number;
  memory_usage_mb: number;
  cpu_usage_percent: number;
  storage_free_gb: number;
  storage_total_gb: number;
  uptime_seconds: number;
  agent_version: string;
  accessibility_active: boolean;
}

export const pairingApi = {
  async getStatus(token?: string) {
    const params: Record<string, string> = {};
    if (token) params.token = token;
    const res = await api.get<PairingStatus>('/api/pairing/status', { params });
    return res.data;
  },

  async discoverUSB(token?: string) {
    const params: Record<string, string> = {};
    if (token) params.token = token;
    const res = await api.post<{
      success: boolean;
      devices_found: number;
      devices: USBDeviceInfo[];
      message?: string;
    }>('/api/pairing/usb/discover', {}, { params });
    return res.data;
  },

  async connectUSB(serial: string, token?: string) {
    const params: Record<string, string> = {};
    if (token) params.token = token;
    const res = await api.post<{
      success: boolean;
      message: string;
      serial: string;
      workflow_id: string;
      device_info: USBDeviceInfo;
    }>('/api/pairing/usb/connect', { serial }, { params });
    return res.data;
  },

  async verifyUSB(serial: string, token?: string) {
    const params: Record<string, string> = {};
    if (token) params.token = token;
    const res = await api.post<{
      success: boolean;
      message: string;
      serial: string;
      fingerprint: string;
      fingerprint_data: Record<string, string>;
      device_identity_confirmed: boolean;
    }>('/api/pairing/usb/verify', { serial }, { params });
    return res.data;
  },

  async trustDevice(device_id: string, trust_level = 'always_trusted', token?: string) {
    const params: Record<string, string> = {};
    if (token) params.token = token;
    const res = await api.post<{
      success: boolean;
      message: string;
      device_id: string;
      trust_level: string;
      trust_token: string;
      certificate: string;
    }>('/api/pairing/device/trust', { device_id, trust_level }, { params });
    return res.data;
  },

  async syncPermissions(device_id: string, permissions: Record<string, string>, token?: string) {
    const params: Record<string, string> = {};
    if (token) params.token = token;
    const res = await api.post<{
      success: boolean;
      message: string;
      device_id: string;
      permissions: Record<string, string>;
    }>('/api/pairing/device/permissions', { device_id, permissions }, { params });
    return res.data;
  },

  async registerDevice(serial: string, token?: string) {
    const params: Record<string, string> = {};
    if (token) params.token = token;
    const res = await api.post<{
      success: boolean;
      message: string;
      device_id: string;
      device_name: string;
      manufacturer: string;
      model: string;
    }>('/api/pairing/device/register', { serial }, { params });
    return res.data;
  },

  async createDeviceTwin(serial: string, token?: string) {
    const params: Record<string, string> = {};
    if (token) params.token = token;
    const res = await api.post<{
      success: boolean;
      message: string;
      device_id: string;
      twin: DeviceTwin;
    }>('/api/pairing/device/twin/create', { serial }, { params });
    return res.data;
  },

  async getCurrentDevice(token?: string) {
    const params: Record<string, string> = {};
    if (token) params.token = token;
    const res = await api.get<{
      success: boolean;
      device: (DeviceInfo & {
        charging: boolean;
        foreground_app: string | null;
        foreground_package: string | null;
        screen_state: string | null;
        lock_state: string | null;
        network_type: string | null;
        network_strength: number | null;
        memory_usage_mb: number | null;
        cpu_usage_percent: number | null;
        twin: {
          readiness_score: number | null;
          ai_ready: boolean;
          health_score: number | null;
          trust_score: number | null;
          sync_state: string;
        } | null;
      }) | null;
      message?: string;
    }>('/api/pairing/device/current', { params });
    return res.data;
  },

  async getDeviceTwin(device_id: string, token?: string) {
    const params: Record<string, string> = { device_id };
    if (token) params.token = token;
    const res = await api.get<{ success: boolean; twin: DeviceTwin }>('/api/pairing/device/twin', { params });
    return res.data;
  },

  async getDeviceCapabilities(device_id: string, token?: string) {
    const params: Record<string, string> = { device_id };
    if (token) params.token = token;
    const res = await api.get('/api/pairing/device/capabilities', { params });
    return res.data;
  },

  async getDevicePermissions(device_id: string, token?: string) {
    const params: Record<string, string> = { device_id };
    if (token) params.token = token;
    const res = await api.get('/api/pairing/device/permissions', { params });
    return res.data;
  },

  async getDeviceHeartbeat(device_id: string, token?: string) {
    const params: Record<string, string> = { device_id };
    if (token) params.token = token;
    const res = await api.get<{
      success: boolean;
      online: boolean;
      device_id: string;
      heartbeat: HeartbeatData | null;
    }>('/api/pairing/device/heartbeat', { params });
    return res.data;
  },

  async disconnectDevice(device_id: string, token?: string) {
    const params: Record<string, string> = {};
    if (token) params.token = token;
    const res = await api.post<{ success: boolean; message: string }>(
      '/api/pairing/device/disconnect',
      { device_id },
      { params }
    );
    return res.data;
  },

  getWebSocketUrl(): string {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const wsBase = baseUrl.replace(/^http/, 'ws');
    const token = localStorage.getItem('accessToken') || '';
    return `${wsBase}/ws/device?token=${token}`;
  },
};
