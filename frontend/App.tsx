import React, { useState, useMemo, ChangeEvent } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { GoogleGenAI } from '@google/genai';

interface DataPoint {
  bin: string;
  expected: number;
  actual: number;
}

const calculatePSI = (data: DataPoint[]) => {
  let psi = 0;
  data.forEach(d => {
    const e = d.expected / 100 || 0.0001;
    const a = d.actual / 100 || 0.0001;
    psi += (a - e) * Math.log(a / e);
  });
  return psi;
};

export default function App() {
  const [data, setData] = useState<DataPoint[]>([
    { bin: '0-0.2', expected: 20, actual: 18 },
    { bin: '0.2-0.4', expected: 30, actual: 25 },
    { bin: '0.4-0.6', expected: 25, actual: 30 },
    { bin: '0.6-0.8', expected: 15, actual: 17 },
    { bin: '0.8-1.0', expected: 10, actual: 10 },
  ]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const psiValue = useMemo(() => calculatePSI(data), [data]);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleFileSubmit = () => {
    if (!selectedFile) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      const lines = text.split('\n').slice(1);
      const newData: DataPoint[] = lines.map(line => {
        const [bin, expected, actual] = line.split(',');
        return { bin, expected: parseFloat(expected), actual: parseFloat(actual) };
      }).filter(d => d.bin);
      setData(newData);
      setAnalysis('');
    };
    reader.readAsText(selectedFile);
  };

  const runAnalysis = async () => {
    setLoading(true);
    try {
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY || '', vertexai: true });
      const prompt = `Analyze this PSI score: ${psiValue.toFixed(4)}. 
      Data: ${JSON.stringify(data)}. 
      Explain if the model is stable (PSI < 0.1 is stable, 0.1-0.25 is minor shift, > 0.25 is significant shift). 
      Provide a concise professional summary.`;
      
      const response = await ai.models.generateContent({
        model: 'gemini-2.5-flash',
        contents: { role: 'user', parts: [{ text: prompt }] }
      });
      setAnalysis(response.text || 'No analysis generated.');
    } catch (e) {
      setAnalysis('Error generating AI insight.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-slate-800">Population Stability Index (PSI) Calculation with AI Summarization</h1>
        <p className="text-slate-600">Upload a CSV file with 3 columns (bin, expected, actual)</p>
      </header>

      <div className="mb-6 p-4 bg-white rounded-lg border border-slate-200 shadow-sm">
        <label className="block text-sm font-medium text-slate-700 mb-2">Upload Data (CSV format: bin,expected,actual)</label>
        <div className="flex gap-4 items-center">
          <input type="file" accept=".csv" onChange={handleFileChange} className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
          <button 
            onClick={handleFileSubmit}
            disabled={!selectedFile}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
          >
            Submit
          </button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <h2 className="text-lg font-semibold mb-4">Distribution Comparison</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="bin" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="expected" stroke="#3b82f6" name="Expected %" />
                <Line type="monotone" dataKey="actual" stroke="#ef4444" name="Actual %" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex flex-col justify-center">
          <div className="text-center">
            <div className="text-sm text-slate-500 uppercase tracking-wider">Current PSI</div>
            <div className={`text-5xl font-bold my-4 ${psiValue > 0.25 ? 'text-red-600' : 'text-blue-600'}`}>
              {psiValue.toFixed(4)}
            </div>
            <button 
              onClick={runAnalysis}
              disabled={loading}
              className="bg-slate-900 text-white px-6 py-2 rounded-lg hover:bg-slate-800 transition"
            >
              {loading ? 'Analyzing...' : 'Get AI Narrative'}
            </button>
          </div>
        </div>
      </div>

      {analysis && (
        <div className="mt-8 p-6 bg-blue-50 rounded-xl border border-blue-100">
          <h3 className="font-bold text-blue-900 mb-2">AI Narrative Summary</h3>
          <p className="text-blue-800 leading-relaxed">{analysis}</p>
        </div>
      )}
    </div>
  );
}