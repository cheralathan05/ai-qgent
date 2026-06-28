import { useState, useEffect, useCallback, useRef } from 'react';
import { pairingApi, type USBDeviceInfo, type NonErrorPairingStep, type DeviceTwin, type HeartbeatData, type WorkflowStatus, ERROR_STATES, CONNECTED_STATES } from '@/lib/api/pairing';

export interface PairingState {
  step: NonErrorPairingStep | 'error';
  progress: number;
  message: string;
  workflowId: string | null;
  serial: string | null;
  deviceId: string | null;
  deviceInfo: USBDeviceInfo | null;
  twin: DeviceTwin | null;
  liveHeartbeat: HeartbeatData | null;
  isOnline: boolean;
  isConnected: boolean;
  paired: boolean;
  trusted: boolean;
  error: string | null;
  loading: boolean;
}

export function useDevicePairing() {
  const [state, setState] = useState<PairingState>({
    step: 'IDLE',
    progress: 0,
    message: 'Ready to pair',
    workflowId: null,
    serial: null,
    deviceId: null,
    deviceInfo: null,
    twin: null,
    liveHeartbeat: null,
    isOnline: false,
    isConnected: false,
    paired: false,
    trusted: false,
    error: null,
    loading: false,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    return () => { mountedRef.current = false; };
  }, []);

  const getToken = useCallback(() => {
    return localStorage.getItem('accessToken') || undefined;
  }, []);

  // Apply workflow status to state
  const applyStatus = useCallback((status: WorkflowStatus, deviceInfo?: USBDeviceInfo | null) => {
    const newStep = status.state || 'IDLE';
    const isErrorStep = ERROR_STATES.has(newStep as NonErrorPairingStep);
    const isConnectedStep = CONNECTED_STATES.has(newStep as NonErrorPairingStep);

    setState(s => ({
      ...s,
      step: isErrorStep ? 'error' : (newStep as NonErrorPairingStep),
      progress: status.progress ?? s.progress,
      message: status.message ?? s.message,
      workflowId: status.workflow_id ?? s.workflowId,
      serial: status.serial ?? s.serial,
      deviceId: status.device_id ?? s.deviceId,
      isOnline: status.connected ?? s.isOnline,
      isConnected: isConnectedStep,
      paired: status.paired ?? s.paired,
      trusted: status.trusted ?? s.trusted,
      error: status.error_message ?? (isErrorStep ? status.state : null),
      loading: false,
      deviceInfo: deviceInfo !== undefined ? (deviceInfo ?? s.deviceInfo) : s.deviceInfo,
    }));
  }, []);

  // Poll backend status every 3 seconds
  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    pollIntervalRef.current = setInterval(async () => {
      try {
        const status = await pairingApi.getStatus(getToken());
        if (mountedRef.current) {
          applyStatus(status);
        }
      } catch {
        // Silently fail - will retry
      }
    }, 3000);
  }, [getToken, applyStatus]);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  // Check initial status
  const checkStatus = useCallback(async () => {
    setState(s => ({ ...s, loading: true }));
    try {
      const status = await pairingApi.getStatus(getToken());
      if (mountedRef.current) {
        applyStatus(status);
      }
      return status;
    } catch {
      if (mountedRef.current) {
        setState(s => ({ ...s, loading: false }));
      }
      return null;
    }
  }, [getToken, applyStatus]);

  // USB Discovery
  const discoverUSB = useCallback(async () => {
    setState(s => ({ ...s, loading: true, error: null }));
    try {
      const result = await pairingApi.discoverUSB(getToken());
      if (mountedRef.current) {
        if (result.devices_found > 0) {
          setState(s => ({
            ...s,
            step: 'DEVICE_FOUND',
            serial: result.devices[0].serial,
            deviceInfo: result.devices[0],
            loading: false,
          }));
        } else {
          setState(s => ({
            ...s,
            step: 'DISCOVERING',
            loading: false,
            error: result.message || 'No USB devices found',
          }));
        }
      }
      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Discovery failed';
      if (mountedRef.current) {
        setState(s => ({ ...s, step: 'error', loading: false, error: msg }));
      }
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
    setState(s => ({ ...s, loading: true, error: null }));
    try {
      const result = await pairingApi.connectUSB(deviceSerial, getToken());
      if (mountedRef.current) {
        setState(s => ({
          ...s,
          step: result.state as NonErrorPairingStep || 'CONNECTED',
          progress: result.progress ?? 25,
          workflowId: result.workflow_id,
          serial: result.serial,
          deviceInfo: result.device_info,
          loading: false,
        }));
      }
      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Connection failed';
      if (mountedRef.current) {
        setState(s => ({ ...s, step: 'error', loading: false, error: msg }));
      }
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
    setState(s => ({ ...s, loading: true }));
    try {
      const result = await pairingApi.verifyUSB(deviceSerial, getToken());
      if (mountedRef.current) {
        if (result.state === 'VERIFICATION_FAILED' || result.state === 'TIMEOUT' || !result.success) {
          setState(s => ({
            ...s,
            step: 'error',
            loading: false,
            error: result.message || 'Verification failed',
          }));
        } else if (result.state === 'VERIFIED') {
          setState(s => ({
            ...s,
            step: 'VERIFIED',
            progress: 50,
            loading: false,
            error: null,
          }));
        } else {
          setState(s => ({
            ...s,
            step: result.state as NonErrorPairingStep,
            progress: result.progress ?? 35,
            loading: false,
          }));
        }
      }
      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Verification failed';
      if (mountedRef.current) {
        setState(s => ({ ...s, step: 'error', loading: false, error: msg }));
      }
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
    setState(s => ({ ...s, loading: true }));
    try {
      const result = await pairingApi.trustDevice(devId, 'always_trusted', getToken());
      if (mountedRef.current) {
        setState(s => ({
          ...s,
          step: result.state as NonErrorPairingStep || 'TRUSTED',
          progress: result.progress ?? 60,
          loading: false,
          trusted: true,
        }));
      }
      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Trust failed';
      if (mountedRef.current) {
        setState(s => ({ ...s, step: 'error', loading: false, error: msg }));
      }
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
    setState(s => ({ ...s, loading: true }));
    try {
      const result = await pairingApi.syncPermissions(devId, perms, getToken());
      if (mountedRef.current) {
        setState(s => ({
          ...s,
          step: result.state as NonErrorPairingStep || 'PERMISSION_SYNC',
          progress: result.progress ?? 65,
          loading: false,
        }));
      }
      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Permission sync failed';
      if (mountedRef.current) {
        setState(s => ({ ...s, step: 'error', loading: false, error: msg }));
      }
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
    setState(s => ({ ...s, loading: true }));
    try {
      const result = await pairingApi.registerDevice(deviceSerial, getToken());
      if (mountedRef.current) {
        setState(s => ({
          ...s,
          step: result.state as NonErrorPairingStep || 'DEVICE_REGISTERED',
          progress: result.progress ?? 75,
          deviceId: result.device_id,
          deviceInfo: s.deviceInfo ? { ...s.deviceInfo, device_name: result.device_name } : s.deviceInfo,
          loading: false,
        }));
      }
      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Registration failed';
      if (mountedRef.current) {
        setState(s => ({ ...s, step: 'error', loading: false, error: msg }));
      }
      return null;
    }
  }, [state.serial, getToken]);

  // Create Device Twin (also transitions to READY)
  const createTwin = useCallback(async (serial?: string) => {
    const deviceSerial = serial || state.serial;
    if (!deviceSerial) {
      setState(s => ({ ...s, error: 'No device serial', step: 'error' }));
      return null;
    }
    setState(s => ({ ...s, loading: true }));
    try {
      const result = await pairingApi.createDeviceTwin(deviceSerial, getToken());
      if (mountedRef.current) {
        setState(s => ({
          ...s,
          step: result.state as NonErrorPairingStep || 'READY',
          progress: result.progress ?? 95,
          deviceId: result.device_id,
          twin: result.twin,
          isConnected: true,
          loading: false,
        }));
      }
      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Twin creation failed';
      if (mountedRef.current) {
        setState(s => ({ ...s, step: 'error', loading: false, error: msg }));
      }
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
    if (mountedRef.current) {
      setState({
        step: 'IDLE', progress: 0, message: 'Ready to pair',
        workflowId: null, serial: null, deviceId: null,
        deviceInfo: null, twin: null, liveHeartbeat: null,
        isOnline: false, isConnected: false, paired: false, trusted: false,
        error: null, loading: false,
      });
    }
  }, [state.deviceId, getToken]);

  // WebSocket connection for real-time pairing events
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const url = pairingApi.getWebSocketUrl();
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        // Send auth token
        const token = getToken();
        ws.send(JSON.stringify({ type: 'auth', token }));

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
          const eventType = msg.event || '';

          // Handle state sync events from the backend
          if (eventType === 'STATE_SYNC' && msg.data) {
            if (mountedRef.current) applyStatus(msg.data);
          } else if (eventType === 'DISCOVERING' || eventType === 'DEVICE_FOUND') {
            if (mountedRef.current) applyStatus(msg.data);
          } else if (eventType === 'CONNECTING' || eventType === 'CONNECTED') {
            if (mountedRef.current) applyStatus(msg.data);
          } else if (eventType === 'VERIFYING' || eventType === 'VERIFIED') {
            if (mountedRef.current) applyStatus(msg.data);
          } else if (eventType === 'TRUSTED') {
            if (mountedRef.current) {
              setState(s => ({ ...s, trusted: true }));
              applyStatus(msg.data);
            }
          } else if (eventType === 'PERMISSIONS') {
            if (mountedRef.current) applyStatus(msg.data);
          } else if (eventType === 'REGISTERING' || eventType === 'DEVICE_REGISTERED') {
            if (mountedRef.current) applyStatus(msg.data);
          } else if (eventType === 'DEVICE_TWIN_CREATED' || eventType === 'READY' || eventType === 'ACTIVE') {
            if (mountedRef.current) {
              applyStatus(msg.data);
            }
          } else if (eventType === 'USB_DISCONNECTED' || eventType === 'DEVICE_REMOVED') {
            if (mountedRef.current) {
              setState(s => ({
                ...s,
                step: 'error',
                isOnline: false,
                isConnected: false,
                error: msg.data?.message || 'Device disconnected',
              }));
            }
          } else if (eventType === 'VERIFICATION_FAILED' || eventType === 'TIMEOUT' || eventType === 'PAIRING_FAILED') {
            if (mountedRef.current) {
              setState(s => ({
                ...s,
                step: 'error',
                error: msg.data?.error_message || msg.data?.message || 'Pairing failed',
              }));
            }
          } else if (eventType === 'CANCELLED') {
            if (mountedRef.current) {
              setState(s => ({
                ...s,
                step: 'IDLE',
                error: msg.data?.message || 'Cancelled',
              }));
            }
          } else if (eventType === 'SESSION_CANCELLED') {
            if (mountedRef.current) {
              setState(s => ({
                ...s,
                step: 'error',
                error: 'Another pairing session started',
              }));
            }
          } else if (eventType === 'HEARTBEAT') {
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
        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(() => connectWebSocket(), 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {}
  }, [getToken, applyStatus]);

  // Start polling when component mounts
  useEffect(() => {
    startPolling();
    return () => {
      stopPolling();
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [startPolling, stopPolling]);

  // Auto-connect WebSocket when a workflow is active
  useEffect(() => {
    if (state.workflowId && state.step !== 'IDLE' && state.step !== 'error') {
      connectWebSocket();
    }
  }, [state.workflowId, state.step, connectWebSocket]);

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
  };
}
