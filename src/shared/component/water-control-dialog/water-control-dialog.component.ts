import { HttpClient } from '@angular/common/http';
import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-water-control-dialog',
  templateUrl: './water-control-dialog.component.html',
  styleUrls: ['./water-control-dialog.component.scss']
})
export class WaterControlDialogComponent implements OnInit {
  public controlStatus: 'IDLE' | 'LOADING' | 'SUCCESS' | 'FAILED' = 'IDLE';
  public activeAction: 'pause' | 'resume' | '' = '';
  public statusMessage: string = '';
  public url = environment.api;

  constructor(
    private http: HttpClient,
    @Inject(MAT_DIALOG_DATA) public dialogData: any,
    public dialogRef: MatDialogRef<WaterControlDialogComponent>
  ) { }

  ngOnInit(): void { }

  async executeWaterControl(mode: 'pause' | 'resume') {
    this.activeAction = mode;
    this.controlStatus = 'LOADING';
    const endpoint = `${this.url}/system/watercon/${mode}`;

    this.http.get<any>(endpoint).subscribe({
      next: (res) => {
        console.log('Water control response:', res);
        this.controlStatus = 'SUCCESS';
        this.statusMessage = mode === 'pause' ? 'Water Flow Paused Successfully' : 'Water Flow Resumed Successfully';
        setTimeout(() => {
          this.dialogRef.close({ success: true, mode, res });
        }, 1500);
      },
      error: (err) => {
        console.error('Water control error:', err);
        this.controlStatus = 'FAILED';
        this.statusMessage = `Failed to ${mode} water flow. Please try again.`;
      }
    });
  }

  resetStatus() {
    this.controlStatus = 'IDLE';
    this.activeAction = '';
    this.statusMessage = '';
  }

  close() {
    this.dialogRef.close();
  }
}
