import { useState, useEffect, useCallback, useRef } from 'react';
import { pairingApi, type USBDeviceInfo, type PairingStep, type DeviceTwin, type HeartbeatData } from '@/lib/api/pairing';

export interface PairingState {
  step: PairingStep;
  workflowId: string | null;
  serial: string | null;
  deviceId: string | null;
  deviceInfo: USBDeviceInfo | null;
  twin: DeviceTwin | null;
  liveHeartbeat: HeartbeatData | null;
  isOnline: boolean;
  error: string | null;
  loading: boolean;
}

export function useDevicePairing() {
  const [state, setState] = useState<PairingState>({
    step: 'idle',
    workflowId: null,
    serial: null,
    deviceId: null,
    deviceInfo: null,
    twin: null,
    liveHeartbeat: null,
    isOnline: false,
    error: null,
    loading: false,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const getToken = useCallback(() => {
    return localStorage.getItem('accessToken') || undefined;
  }, []);

  // Check initial status
  const checkStatus = useCallback(async () => {
    try {
      const status = await pairingApi.getStatus(getToken());
      setState(s => ({
        ...s,
        step: status.workflow_state,
        serial: status.active_session?.serial || null,
        deviceId: status.active_session?.device_id || null,
        deviceInfo: status.active_session ? {
          serial: status.active_session.serial,
          manufacturer: status.active_session.manufacturer,
          model: status.active_session.model,
          // Fill defaults for remaining fields
          brand: '', android_version: '', sdk_version: 0, build_number: '',
          battery_percentage: 0, charging: false, screen_width: 0, screen_height: 0,
          cpu_abi: '', ram_total_kb: 0, storage_total_bytes: 0, foreground_app: '',
          screen_on: false, lock_state: '', usb_debugging: false, developer_options: false,
          accessibility_service: false, device_name: '', adb_authorized: false, connection_quality: '',
        } : null,
        isOnline: status.devices.some(d => d.is_online),
      }));
      return status;
    } catch {
      return null;
    }
  }, [getToken]);

  // USB Discovery
  const discoverUSB = useCallback(async () => {
    setState(s => ({ ...s, loading: true, error: null, step: 'discovering' }));
    try {
      const result = await pairingApi.discoverUSB(getToken());
      if (result.devices_found > 0) {
        const device = result.devices[0];
        setState(s => ({
          ...s,
          step: 'discovering',
          serial: device.serial,
          deviceInfo: device,
          loading: false,
        }));
        return result;
      }
      setState(s => ({ ...s, step: 'idle', loading: false, error: 'No USB devices found' }));
      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Discovery failed';
      setState(s => ({ ...s, step: 'error', loading: false, error: msg }));
      return null;
    }
  }, [getToken]);

  // USB Connect
  const connectUSB = useCallback(async (serial?: string) => {
    const deviceSerial = serial || state.serial;
    if (!deviceSerial) {
      setState(s => ({ ...s, error: 'No device serial', step: 'error' }));
      return null;
    }
    setState(s => ({ ...s, loading: true, error: null, step: 'connecting' }));
    try {
      const result = await pairingApi.connectUSB(deviceSerial, getToken());
      setState(s => ({
        ...s,
        step: 'connecting',
        workflowId: result.workflow_id,
        deviceId: result.workflow_id,
        serial: result.serial,
        deviceInfo: result.device_info,
        loading: false,
      }));
      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Connection failed';
      setState(s => ({ ...s, step: 'error', loading: false, error: msg }));
      return null;
    }
  }, [state.serial, getToken]);

  // Verify Device
  const verifyDevice = useCallback(async (serial?: string) => {
    const deviceSerial = serial || state.serial;
    if (!deviceSerial) {
      setState(s => ({ ...s, error: 'No device serial', step: 'error' }));
      return null;
    }
    setState(s => ({ ...s, loading: true, step: 'verifying' }));
    try {
      const result = await pairingApi.verifyUSB(deviceSerial, getToken());
      setState(s => ({ ...s, step: 'verifying', loading: false, error: null }));
      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Verification failed';
      setState(s => ({ ...s, step: 'error', loading: false, error: msg }));
      return null;
    }
  }, [state.serial, getToken]);

  // Trust Device
  const trustDevice = useCallback(async (deviceId?: string) => {
    const devId = deviceId || state.deviceId;
    if (!devId) {
      setState(s => ({ ...s, error: 'No device ID', step: 'error' }));
      return null;
    }
    setState(s => ({ ...s, loading: true, step: 'trusting' }));
    try {
      const result = await pairingApi.trustDevice(devId, 'always_trusted', getToken());
      setState(s => ({ ...s, step: 'trusting', loading: false }));
      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Trust failed';
      setState(s => ({ ...s, step: 'error', loading: false, error: msg }));
      return null;
    }
  }, [state.deviceId, getToken]);

  // Sync Permissions
  const syncPermissions = useCallback(async (deviceId?: string, permissions?: Record<string, string>) => {
    const devId = deviceId || state.deviceId;
    if (!devId) {
      setState(s => ({ ...s, error: 'No device ID', step: 'error' }));
      return null;
    }
    const perms = permissions || {
      screen_capture: 'granted',
      navigation: 'granted',
      notifications: 'granted',
      overlay: 'granted',
      accessibility: 'granted',
      files: 'granted',
      camera: 'granted',
      microphone: 'granted',
    };
    setState(s => ({ ...s, loading: true, step: 'permissions' }));
    try {
      const result = await pairingApi.syncPermissions(devId, perms, getToken());
      setState(s => ({ ...s, step: 'permissions', loading: false }));
      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Permission sync failed';
      setState(s => ({ ...s, step: 'error', loading: false, error: msg }));
      return null;
    }
  }, [state.deviceId, getToken]);

  // Register Device
  const registerDevice = useCallback(async (serial?: string) => {
    const deviceSerial = serial || state.serial;
    if (!deviceSerial) {
      setState(s => ({ ...s, error: 'No device serial', step: 'error' }));
      return null;
    }
    setState(s => ({ ...s, loading: true, step: 'registering' }));
    try {
      const result = await pairingApi.registerDevice(deviceSerial, getToken());
      setState(s => ({
        ...s,
        step: 'registering',
        deviceId: result.device_id,
        deviceInfo: s.deviceInfo ? { ...s.deviceInfo, device_name: result.device_name } : s.deviceInfo,
        loading: false,
      }));
      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Registration failed';
      setState(s => ({ ...s, step: 'error', loading: false, error: msg }));
      return null;
    }
  }, [state.serial, getToken]);

  // Create Device Twin
  const createTwin = useCallback(async (serial?: string) => {
    const deviceSerial = serial || state.serial;
    if (!deviceSerial) {
      setState(s => ({ ...s, error: 'No device serial', step: 'error' }));
      return null;
    }
    setState(s => ({ ...s, loading: true, step: 'twin_creating' }));
    try {
      const result = await pairingApi.createDeviceTwin(deviceSerial, getToken());
      setState(s => ({
        ...s,
        step: 'ready',
        deviceId: result.device_id,
        twin: result.twin,
        loading: false,
      }));
      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Twin creation failed';
      setState(s => ({ ...s, step: 'error', loading: false, error: msg }));
      return null;
    }
  }, [state.serial, getToken]);

  // Disconnect Device
  const disconnect = useCallback(async (deviceId?: string) => {
    const devId = deviceId || state.deviceId;
    if (!devId) return;
    try {
      await pairingApi.disconnectDevice(devId, getToken());
    } catch {}
    setState({
      step: 'idle', workflowId: null, serial: null, deviceId: null,
      deviceInfo: null, twin: null, liveHeartbeat: null, isOnline: false,
      error: null, loading: false,
    });
  }, [state.deviceId, getToken]);

  // WebSocket connection for live updates
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const url = pairingApi.getWebSocketUrl();
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        // Subscribe to device updates
        if (state.deviceId) {
          ws.send(JSON.stringify({ type: 'subscribe', device_id: state.deviceId }));
        }
        // Start sending regular pings
        if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          const eventType = msg.event || msg.type;

          if (eventType === 'HEARTBEAT') {
            setState(s => ({
              ...s,
              liveHeartbeat: {
                battery_level: msg.battery_level,
                battery_charging: msg.battery_charging,
                foreground_app: msg.foreground_app,
                foreground_package: msg.foreground_package,
                current_activity: msg.current_activity,
                screen_state: msg.screen_state,
                lock_state: msg.lock_state,
                network_type: msg.network_type || '',
                network_strength: msg.network_strength || 0,
                memory_usage_mb: msg.memory_usage_mb || 0,
                cpu_usage_percent: msg.cpu_usage_percent || 0,
                storage_free_gb: msg.storage_free_gb || 0,
                storage_total_gb: msg.storage_total_gb || 0,
                uptime_seconds: msg.uptime_seconds || 0,
                agent_version: msg.agent_version || '',
                accessibility_active: msg.accessibility_active || false,
              },
              isOnline: true,
            }));
          } else if (eventType === 'DEVICE_DISCONNECTED') {
            setState(s => ({ ...s, isOnline: false }));
          } else if (eventType === 'DEVICE_RECONNECTED') {
            setState(s => ({ ...s, isOnline: true }));
          }
        } catch {}
      };

      ws.onclose = () => {
        if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
        // Auto reconnect after 3s
        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(() => connectWebSocket(), 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {}
  }, [state.deviceId]);

  // Run full pairing workflow
  const runFullPairing = useCallback(async () => {
    // Step 1: Discover
    const discoverResult = await discoverUSB();
    if (!discoverResult || discoverResult.devices_found === 0) return false;
    const serial = discoverResult.devices[0].serial;

    // Step 2: Connect
    const connectResult = await connectUSB(serial);
    if (!connectResult) return false;

    // Step 3: Verify
    const verifyResult = await verifyDevice(serial);
    if (!verifyResult) return false;

    // Step 4: Register
    const registerResult = await registerDevice(serial);
    if (!registerResult) return false;
    const deviceId = registerResult.device_id;

    // Step 5: Trust
    const trustResult = await trustDevice(deviceId);
    if (!trustResult) return false;

    // Step 6: Permissions
    const permResult = await syncPermissions(deviceId);
    if (!permResult) return false;

    // Step 7: Create Twin
    const twinResult = await createTwin(serial);
    if (!twinResult) return false;

    // Connect WebSocket for live updates
    connectWebSocket();
    return true;
  }, [discoverUSB, connectUSB, verifyDevice, registerDevice, trustDevice, syncPermissions, createTwin, connectWebSocket]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  return {
    ...state,
    checkStatus,
    discoverUSB,
    connectUSB,
    verifyDevice,
    trustDevice,
    syncPermissions,
    registerDevice,
    createTwin,
    disconnect,
    connectWebSocket,
    runFullPairing,
  };
}
