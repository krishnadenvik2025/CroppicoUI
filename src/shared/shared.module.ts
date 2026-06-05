import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CalibrationDialogComponent } from './component/calibration-dialog/calibration-dialog.component';
import { AuthComponent } from './component/auth/auth.component';
import { MaterialModule } from 'src/assets/material/material.module';
import { MatKeyboardModule } from 'angular-onscreen-material-keyboard';
import { FlushDialogComponent } from './component/flush-dialog/flush-dialog.component';
import { ChartsComponent } from './component/charts/charts.component';
import { NgApexchartsModule } from "ng-apexcharts";
import { GuideComponent } from './component/guide/guide.component';
import { PdfViewerModule } from 'ng2-pdf-viewer';
import { TopupDialogComponent } from './component/topup-dialog/topup-dialog.component';

@NgModule({
  declarations: [
    CalibrationDialogComponent,
    AuthComponent,
    FlushDialogComponent,
    ChartsComponent,
    GuideComponent,
    TopupDialogComponent],
  imports: [
    CommonModule,
    MaterialModule,
    MatKeyboardModule,
    NgApexchartsModule,
    PdfViewerModule

  ]
})
export class SharedModule { }
