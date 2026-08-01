import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import { Dropzone } from './components/Analyze/Dropzone';
import { ImageComparison } from './components/Analyze/ImageComparison';
import { StatCards } from './components/Analyze/StatCards';
import { TurbidityComparison } from './components/Analyze/TurbidityComparison';
import { WaterQualityBadge } from './components/Analyze/WaterQualityBadge';

import { CalibrationTable } from './components/Calibration/CalibrationTable';
import { CalibrationCharts } from './components/Calibration/CalibrationCharts';

import { HistoryTable } from './components/History/HistoryTable';
import { CameraView } from './components/LiveCamera/CameraView';

import {
  analyzeImage,
  fetchCalibration,
  updateCalibration,
  refitCalibration,
  fetchHistory,
  clearHistory,
  fetchSamples,
} from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('analyze');
  const [darkMode, setDarkMode] = useState(true);
  const [backendOnline, setBackendOnline] = useState(true);

  // Analysis State
  const [analysisResult, setAnalysisResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Calibration State
  const [calibrationData, setCalibrationData] = useState(null);
  const [modelsSummary, setModelsSummary] = useState(null);
  const [calibLoading, setCalibLoading] = useState(false);

  // History State
  const [historyData, setHistoryData] = useState([]);

  // Preset Samples State
  const [samplePresets, setSamplePresets] = useState([]);

  // Check health & load initial calibration + history
  useEffect(() => {
    checkHealth();
    loadCalibrationData();
    loadHistoryData();
    loadPresets();
  }, []);

  const checkHealth = async () => {
    try {
      const res = await fetch('/api/');
      if (res.ok) setBackendOnline(true);
      else setBackendOnline(false);
    } catch (e) {
      setBackendOnline(false);
    }
  };

  const loadCalibrationData = async () => {
    try {
      setCalibLoading(true);
      const res = await fetchCalibration();
      setCalibrationData(res.datasets);
      setModelsSummary(res.models_summary);
    } catch (err) {
      console.error('Error fetching calibration data:', err);
    } finally {
      setCalibLoading(false);
    }
  };

  const loadHistoryData = async () => {
    try {
      const res = await fetchHistory();
      setHistoryData(res);
    } catch (err) {
      console.error('Error fetching history:', err);
    }
  };

  const loadPresets = async () => {
    try {
      const res = await fetchSamples();
      setSamplePresets(res);
    } catch (err) {
      console.error('Error fetching presets:', err);
    }
  };

  // Image Upload Analysis Handler
  const handleFileSelect = async (file) => {
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeImage(file);
      if (data.error) {
        setError(data.error);
        setAnalysisResult(null);
      } else {
        setAnalysisResult(data);
        setError(null);
        loadHistoryData(); // Refresh history
      }
    } catch (err) {
      setError(err.message || 'Server error while running OpenCV image analysis.');
      setAnalysisResult(null);
    } finally {
      setLoading(false);
    }
  };

  // Preset Sample Click Handler
  const handleSampleSelect = async (targetNtu) => {
    setLoading(true);
    setError(null);
    try {
      const preset = samplePresets.find((p) => p.ntu === targetNtu);
      if (!preset) {
        // Fallback fetch presets again
        const fresh = await fetchSamples();
        const found = fresh.find((p) => p.ntu === targetNtu);
        if (found) {
          const res = await fetch(found.image_b64);
          const blob = await res.blob();
          const file = new File([blob], `sample_${targetNtu}_ntu.jpg`, { type: 'image/jpeg' });
          await handleFileSelect(file);
        }
        return;
      }

      const res = await fetch(preset.image_b64);
      const blob = await res.blob();
      const file = new File([blob], `sample_${targetNtu}_ntu.jpg`, { type: 'image/jpeg' });
      await handleFileSelect(file);
    } catch (err) {
      setError('Failed to process preset sample image.');
    } finally {
      setLoading(false);
    }
  };

  // Calibration Update Handler
  const handleCalibrationUpdate = async (newData) => {
    try {
      setCalibLoading(true);
      const res = await updateCalibration(newData);
      setCalibrationData(res.datasets);
      setModelsSummary(res.models_summary);
    } catch (err) {
      console.error('Error updating calibration:', err);
    } finally {
      setCalibLoading(false);
    }
  };

  // Calibration Refit Handler
  const handleCalibrationRefit = async () => {
    try {
      setCalibLoading(true);
      const res = await refitCalibration();
      setModelsSummary(res.models_summary);
    } catch (err) {
      console.error('Error refitting calibration:', err);
    } finally {
      setCalibLoading(false);
    }
  };

  // Clear History Handler
  const handleClearHistory = async () => {
    try {
      await clearHistory();
      setHistoryData([]);
    } catch (err) {
      console.error('Error clearing history:', err);
    }
  };

  return (
    <div className={darkMode ? 'dark bg-lab-950 text-slate-100 min-h-screen' : 'bg-slate-50 text-slate-900 min-h-screen'}>
      
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        darkMode={darkMode}
        setDarkMode={setDarkMode}
        backendOnline={backendOnline}
      />

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

        {/* Tab 1: Analyze */}
        {activeTab === 'analyze' && (
          <div className="space-y-6 animate-fade-in">
            {/* Upload Zone & Sample Launch */}
            <Dropzone
              onFileSelect={handleFileSelect}
              onSampleSelect={handleSampleSelect}
              loading={loading}
              error={error}
            />

            {/* Analysis Results View */}
            {analysisResult && (
              <div className="space-y-6 border-t border-slate-800/80 pt-6">
                
                {/* WHO Water Quality Banner */}
                <WaterQualityBadge
                  waterQuality={analysisResult.water_quality}
                  primaryNtu={analysisResult.primary_ntu}
                />

                {/* Multi-method Turbidity Predictions */}
                <TurbidityComparison data={analysisResult} />

                {/* Original vs OpenCV Mask Viewer */}
                <ImageComparison
                  originalB64={analysisResult.original_image_base64}
                  annotatedB64={analysisResult.annotated_image_base64}
                  shape={analysisResult.shape}
                  centroid={analysisResult.centroid}
                />

                {/* 9 Extracted OpenCV Parameters */}
                <StatCards data={analysisResult} />
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Calibration */}
        {activeTab === 'calibration' && (
          <div className="space-y-6 animate-fade-in">
            <CalibrationTable
              calibrationData={calibrationData || {}}
              onUpdate={handleCalibrationUpdate}
              onRefit={handleCalibrationRefit}
              loading={calibLoading}
            />

            <CalibrationCharts
              datasets={calibrationData}
              modelsSummary={modelsSummary}
            />
          </div>
        )}

        {/* Tab 3: History */}
        {activeTab === 'history' && (
          <div className="animate-fade-in">
            <HistoryTable
              historyData={historyData}
              onClearHistory={handleClearHistory}
            />
          </div>
        )}

        {/* Tab 4: Live Camera */}
        {activeTab === 'camera' && (
          <div className="space-y-6 animate-fade-in">
            <CameraView
              onCaptureAnalyze={(file) => {
                setActiveTab('analyze');
                handleFileSelect(file);
              }}
              loading={loading}
            />
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-6 text-center text-xs font-mono text-slate-500">
        <p>AquaSpot Laser Turbidity Analyzer · OpenCV v4.8 Python Backend · WHO / BIS Standard Compliance</p>
      </footer>
    </div>
  );
}
