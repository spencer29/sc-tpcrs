import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import { AssessmentsPage } from "./routes/AssessmentsPage";
import { CompliancePage } from "./routes/CompliancePage";
import { DashboardLayout } from "./routes/DashboardLayout";
import { LoginPage } from "./routes/LoginPage";
import { RiskDashboardPage } from "./routes/RiskDashboardPage";
import { SupplyChainPage } from "./routes/SupplyChainPage";
import { VendorDetailPage } from "./routes/VendorDetailPage";
import { VendorListPage } from "./routes/VendorListPage";
import { VendorOnboardingWizard } from "./routes/VendorOnboardingWizard";

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <DashboardLayout />
            </RequireAuth>
          }
        >
          <Route index element={<RiskDashboardPage />} />
          <Route path="vendors" element={<VendorListPage />} />
          <Route path="assessments" element={<AssessmentsPage />} />
          <Route path="compliance" element={<CompliancePage />} />
          <Route path="supply-chain" element={<SupplyChainPage />} />
          <Route path="vendors/new" element={<VendorOnboardingWizard />} />
          <Route path="vendors/:vendorId" element={<VendorDetailPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
